"""Shared logic for AI Job Finder: sources, matching, search and tracker helpers.

app.py is the Streamlit entry point; each page lives in views/. Keep page
rendering out of this module so it stays importable and testable.
"""
import re
import csv
import json
import hashlib
import html
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote
from urllib.error import HTTPError, URLError
from io import BytesIO
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from datetime import date, datetime, timedelta, timezone
from collections import Counter
import streamlit as st
import fitz
from docx import Document
import pandas as pd
from ranked_breakdowns import evidence_index, evidence_sort_key, breakdowns_json, breakdowns_csv_rows
from build_info import MATCHING_ENGINE_VERSION, needs_search_refresh, export_filename
from evidence_context import affirmative_match
import tracker_sync
from copy import deepcopy
from career_priority import career_sort_key, career_review_category, has_detailed_description, order_for_review
from coverage_health import coverage_messages
from source_support import with_recovery_links
from employer_evidence import attach_saved_evidence
from description_quality import assess_description
from search_task import SearchTask
from workspace_recovery import prepare_restore
from match_review import review_rows, export_review, evaluate_review
from tracker_store import make_workspace
from source_http import check_cancelled
from posting_metadata import (
    affirmative, declared_arrangement, from_explicit_description,
    strict_onsite_requirement,
    employer_identity_kind, greenhouse_workplace_label,
    reconcile_workplace_record, rss_workplace_style
)
from employer_ui import render_employer_checker
from employer_postings import posting_quality
from official_bulletins import enrich_priority_government_jobs
from government_feed_identity import belongs_to_configured_agency, dedupe_vacancy_urls
from qualification_matcher import CAPABILITIES, compile_resume_profile, assess_job_qualifications
from posting_requirements import _clean as clean_posting_text
from ui_theme import APP_CSS, brand, hero, listing_head
from career_profile import (PROFILE_QUESTIONS, YN_CHOICES, LEGACY_DEFAULT_ANSWERS,
                            profile_areas, interpret_resume)
from role_families import LABELS as ROLE_FAMILY_LABELS, family_for_title, rank_families, explain_job
import saved_searches
from tailoring import build_sheet, sheet_text
import job_workflow as _job_workflow
from job_workflow import (
    distinct_posting_key, canonical_job_url, posting_id, annotate_new_results,
    preferences_allow, explicitly_remote_title
)


def permitted_remote_source(job):
    """Safe startup if Streamlit publishes app.py before its helper module.

    Always prefer the current shared policy function. An older cached
    job_workflow.py may not have the new government-remote function yet,
    even though that symbol already exists on GitHub's main branch.
    Do not crash at import time during that short deployment mismatch.
    """
    check=getattr(_job_workflow,'permitted_remote_source',None)
    if callable(check):
        return check(job)
    source=str(job.get('source') or '')
    if source=='Mayo Clinic' and str(job.get('company') or '').strip()=='Mayo Clinic':
        return True
    return (job.get('government') is True and source in
            ('NEOGOV','NEOED Schooljobs','NYC Open Data'))
from tracker_store import (
    COLUMNS as TRACKER_COLUMNS, STATUSES as TRACKER_STATUSES,
    import_tracker_csv, export_tracker_csv, import_workspace_json,
    export_workspace_json, load_remote_workspace, save_remote_workspace,
    authenticate, upcoming_followups, complete_followup
)


STATUSES = ['Saved','Applied','Interviewing','Offer','Rejected','Skipped','Withdrawn']


# Streamlit 1.41's download buttons rerun the app by default. A fragment
# prevents that rerun, keeping results, page number and active top tab in place.
# Render the same real, native download button on every export page.
@st.fragment
def download_file_widget(label,data,filename,mime,key):
    if isinstance(data,str):
        data=data.encode('utf-8-sig' if mime=='text/csv' else 'utf-8')
    st.download_button(
        label=label,data=data,file_name=filename,mime=mime,
        key=key,use_container_width=True
    )


@st.fragment
def ranked_exports(all_results,run_id):
    """Always allow an export after a completed search, with or without a CV.

    File downloads are isolated from app reruns and preserve real job URLs
    and whatever qualification evidence is available for that search.
    """
    all_results=attach_saved_evidence(all_results,st.session_state.get('employer_checks',{}))
    all_breakdowns=breakdowns_json(
        all_results,matching_version=MATCHING_ENGINE_VERSION,
        search_run_id=run_id)
    flat_breakdowns=breakdowns_csv_rows(
        all_results,matching_version=MATCHING_ENGINE_VERSION,
        search_run_id=run_id)
    csv_data=pd.DataFrame(flat_breakdowns).to_csv(index=False).encode('utf-8-sig')
    json_data=json.dumps(
        all_breakdowns,indent=2,ensure_ascii=False).encode('utf-8')
    with st.container(border=True):
        st.markdown('### Download search results')
        st.caption(f'{len(all_results):,} vacancies · CSV for spreadsheets or JSON for detailed records')
        csv_col,json_col=st.columns(2,gap='medium')
        with csv_col:
            st.download_button(
                'Download CSV',data=csv_data,
                file_name=export_filename('ranked',run_id,'csv'),
                mime='text/csv',key='ranked_export_csv',use_container_width=True)
        with json_col:
            st.download_button(
                'Download JSON',data=json_data,
                file_name=export_filename('detailed',run_id,'json'),
                mime='application/json',key='ranked_export_json',
                use_container_width=True)


def extract_resume_text(file):
    data = file.getvalue()
    name = file.name.lower()
    if name.endswith('.pdf'):
        with fitz.open(stream=data, filetype='pdf') as doc:
            return '\n'.join(page.get_text() for page in doc)
    if name.endswith('.docx'):
        doc = Document(BytesIO(data))
        lines = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    lines.append(cell.text)
        return '\n'.join(lines)
    if name.endswith('.txt'):
        return data.decode('utf-8-sig', errors='replace')
    return ''


def verified_competencies():
    """Areas confirmed in the career profile plus any extra self-confirmations."""
    confirmed, excluded = profile_areas(st.session_state.get('profile_answers'))
    return (confirmed | set(st.session_state.confirmed_qualifications)) - excluded


def excluded_competencies():
    """Areas the person says the resume overstates; matching ignores them."""
    return profile_areas(st.session_state.get('profile_answers'))[1]


def resume_grades():
    """{area: grade} from the resume interpretation, for role-family scoring."""
    text = st.session_state.get('resume_text') or ''
    report = interpret_resume(text, st.session_state.get('profile_answers'))
    return {row['area']: row['grade'] for row in report['areas']}


def verification_editor():
    """Career profile: short answers that confirm or overrule the resume."""
    st.subheader('Your career profile')
    st.write('Resumes leave things out and overstate others. Answer what is true; '
             '**Yes/Partly** gives partial credit for experience the resume does not show, '
             '**No** stops the matcher crediting something the resume implies.')
    answers = st.session_state.profile_answers
    if answers == LEGACY_DEFAULT_ANSWERS:
        st.caption('Pre-filled from the eight responsibilities you confirmed earlier. Review each one.')
    with st.form('career_profile_form'):
        new = {}
        yn = [q for q in PROFILE_QUESTIONS if q['kind'] == 'yn']
        nums = [q for q in PROFILE_QUESTIONS if q['kind'] == 'number']
        left, right = st.columns(2)
        for i, q in enumerate(yn):
            with (left if i % 2 == 0 else right):
                current = answers.get(q['key'], 'Not sure')
                new[q['key']] = st.selectbox(q['question'], YN_CHOICES,
                    index=YN_CHOICES.index(current) if current in YN_CHOICES else 0,
                    key='profile_' + q['key'])
        st.markdown('**Scale** (leave 0 if you prefer not to say)')
        cols = st.columns(len(nums))
        for col, q in zip(cols, nums):
            with col:
                new[q['key']] = int(st.number_input(q['question'], min_value=0, step=1,
                    value=int(answers.get(q['key']) or 0), key='profile_' + q['key']))
        if st.form_submit_button('Save career profile', type='primary'):
            st.session_state.profile_answers = new
            st.session_state.pop('search_results', None)
            st.session_state.pop('search_stats', None)
            saved = persist_tracker_if_unlocked()
            st.success('Profile saved' + (' to your private cloud tracker.' if saved else ' for this session.')
                       + ' Search again to refresh job matches.')
    st.caption('Nothing here is added to your resume automatically. Your answers are saved with your '
               'Job Tracker: in your private cloud database when unlocked, and in tracker backups.')


GRADE_NOTES = {
    'Proven': 'work experience with numbers',
    'Described': 'work experience, no numbers',
    'Volunteer': 'board or volunteer work only',
    'Summary': 'summary or skills list only',
    'Confirmed': 'you confirmed it; resume does not show it',
    'Overruled': 'you said No; matcher ignores the resume wording',
    'Not shown': 'not in resume or profile',
}


def render_resume_interpretation(text):
    """Graded reading of the resume: what is proven, implied, missing or overstated."""
    report = interpret_resume(text, st.session_state.get('profile_answers'))
    st.subheader('How your resume reads')
    counts = Counter(row['grade'] for row in report['areas'])
    a, b, c = st.columns(3)
    a.metric('Proven with numbers', counts['Proven'])
    b.metric('Described, no numbers', counts['Described'])
    c.metric('Bullets with a number', f"{report['numbered_bullets']} of {report['work_bullets']}")
    st.caption('Each skill area is graded by where it appears and whether a number backs it up. '
               'Proven claims count fully in matching; summary-only claims count least.')
    grades = {row['area']: row['grade'] for row in report['areas']}
    st.markdown('**Fields your experience fits best**')
    for fam in rank_families(grades)[:5]:
        gaps = ', '.join(x['area'] for x in fam['gaps'][:2])
        st.write(f"**{fam['score']}%** {fam['label']}" + (f" — gap: {gaps}" if gaps else ''))
    st.caption('Readiness is the share of each field\'s key skills you can show; searches cover all of these fields.')
    table = pd.DataFrame([{'Skill area': row['area'], 'Grade': row['grade'],
                           'What that means': GRADE_NOTES[row['grade']],
                           'Resume line': row['evidence']} for row in report['areas']])
    st.dataframe(table, use_container_width=True, hide_index=True)
    if report['prompts']:
        with st.expander(f"What your resume leaves out ({len(report['prompts'])})", expanded=True):
            for prompt in report['prompts']:
                st.write('• ' + prompt)
    if report['vague']:
        with st.expander(f"Phrases that read as filler ({len(report['vague'])})"):
            st.caption('Recruiters and keyword filters skip these. Replace them with what you did and how much.')
            for item in report['vague']:
                st.write(f"**{item['phrase']}** — {item['line']}")


# Free public remote-job feeds. Cache requests to avoid unnecessary provider traffic.
# Search APIs query the provider directly, rather than filtering only a small
# downloaded feed. Listings must be independently checked before applying.
SEARCH_TERMS = [
    'operations', 'business development', 'general manager', 'marketing',
    'partnerships', 'logistics', 'chief operating officer', 'publisher'
]


# ----------------------- FREE JOB SEARCH ENGINE -----------------------
# No OpenAI, Adzuna, scraping or paid API. Sources load in the background.
# Source coverage is necessarily partial: NEOGOV has per-agency feeds, not
# a public national jobs API. Failed feeds and undated vacancies are excluded.
from concurrent.futures import as_completed
from source_rss import iter_public_rss
from source_http import ContextPool as ThreadPoolExecutor, request_budget, open_response

MAX_POSTING_AGE_DAYS = 45

US_STATES = {
    'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California',
    'CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia',
    'HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas',
    'KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts',
    'MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana',
    'NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico',
    'NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma',
    'OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina',
    'SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont',
    'VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming',
    'DC':'District of Columbia',
}

# Catalog is maintained in job_sources.json, not in this Python file.
# Adding / disabling source boards requires changing only that JSON file.
from pathlib import Path

SOURCE_CATALOG_FILE = Path(__file__).resolve().parent / 'job_sources.json'
VALID_SOURCE_GROUPS = ('neogov', 'neoed', 'lever', 'greenhouse', 'ashby', 'smartrecruiters', 'workable', 'mayo', 'workday')


def read_job_sources(path=SOURCE_CATALOG_FILE):
    if not path.is_file():
        raise FileNotFoundError('job_sources.json is missing. Upload it next to app.py in your GitHub repository.')
    with path.open(encoding='utf-8') as handle:
        config = json.load(handle)
    if config.get('schema_version') != 1:
        raise ValueError('job_sources.json requires schema_version: 1')
    cleaned = {}
    for provider in VALID_SOURCE_GROUPS:
        records = config.get(provider, [])
        if not isinstance(records, list):
            raise ValueError(f'{provider} must be a list in job_sources.json')
        seen, entries = set(), []
        for number, record in enumerate(records, 1):
            if not isinstance(record, dict):
                raise ValueError(f'{provider} item {number} must be an object')
            if record.get('enabled', True) is False:
                continue
            token, name = str(record.get('id', '')).strip(), str(record.get('name', '')).strip()
            if not token or not name or len(token) > 120 or not re.fullmatch(r'[A-Za-z0-9._ -]+', token):
                raise ValueError(f'{provider} item {number}: invalid id or name')
            if token.lower() in seen:
                continue
            seen.add(token.lower())
            state = str(record.get('state', '')).upper().strip()
            if provider in ('neogov', 'neoed'):
                if state not in US_STATES:
                    raise ValueError(f'{provider} item {number}: expected a valid two-letter state')
                entries.append((token, name, state))
            elif provider == 'smartrecruiters':
                entries.append((token, name, bool(record.get('government', False))))
            elif provider == 'workday':
                wd, site = str(record.get('wd', '')).strip(), str(record.get('site', '')).strip()
                if not re.fullmatch(r'wd\d{1,3}', wd) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', site):
                    raise ValueError(f'workday item {number}: expected wd (e.g. wd5) and site')
                entries.append((f'{token.lower()}|{wd}|{site}', name))
            else:
                entries.append((token, name))
        cleaned[provider] = tuple(entries)
    return cleaned


try:
    JOB_SOURCE_CATALOG = read_job_sources()
    JOB_SOURCE_CATALOG_ERROR = ''
except (OSError, ValueError, json.JSONDecodeError) as exc:
    # app.py shows this and stops; the module itself must import cleanly.
    JOB_SOURCE_CATALOG = {group: () for group in VALID_SOURCE_GROUPS}
    JOB_SOURCE_CATALOG_ERROR = str(exc)

GOVERNMENT_AGENCIES = JOB_SOURCE_CATALOG['neogov']
SCHOOLJOBS_AGENCIES = JOB_SOURCE_CATALOG['neoed']
LEVER_BOARDS = JOB_SOURCE_CATALOG['lever']
GREENHOUSE_BOARDS = JOB_SOURCE_CATALOG['greenhouse']
ASHBY_BOARDS = JOB_SOURCE_CATALOG['ashby']
SMARTRECRUITERS_BOARDS = JOB_SOURCE_CATALOG['smartrecruiters']
WORKABLE_BOARDS = JOB_SOURCE_CATALOG['workable']
MAYO_BOARDS = JOB_SOURCE_CATALOG['mayo']
WORKDAY_BOARDS = JOB_SOURCE_CATALOG.get('workday', ())
# JSON edits must invalidate cached employer feeds as well as displayed counts.
SOURCE_CATALOG_VERSION = hashlib.sha256(SOURCE_CATALOG_FILE.read_bytes()).hexdigest()[:16]

# Jobs from government boards may contain unusual occupational titles. These
# patterns cover publisher-adjacent operations, business and civic management.
ROLE_PATTERNS = [
    (r'\b(chief operating officer|coo|chief administrative officer|chief business officer)\b', 'Executive operations', 15),
    (r'\b(city|county|town|village|borough) (administrator|manager)\b', 'Government leadership', 15),
    (r'\b(deputy|assistant) (city|county|town) (administrator|manager)\b', 'Government leadership', 14),
    (r'\b(executive director|managing director|general manager|group publisher|publisher)\b', 'Executive leadership', 13),
    (r'\b(regional|district|area) (operations )?(director|manager|vice president|vp)\b', 'Regional leadership', 13),
    (r'\b(director|vice president|vp|head|chief) of (business development|operations|distribution|marketing|communications|community engagement|community relations|strategic partnerships|digital business|revenue|economic development|administration|administrative services|external affairs|public affairs|public relations)\b', 'Management leadership', 13),
    (r'\b(operations|distribution|logistics|business development|economic development|community engagement|partnerships|communications|marketing|revenue|administrative services|business operations|commercial|digital|public affairs|public relations) (director|manager|lead|vice president|vp)\b', 'Management leadership', 12),
    (r'\b(assistant|deputy|associate) director of (operations|administration|business|community|communications|economic development|distribution|marketing|public works)\b', 'Management leadership', 11),
    (r'\b(program|business|operations|project) (administrator|manager)\b', 'Operations management', 9),
    (r'\b(budget|strategic planning|procurement|contract|vendor|circulation|customer experience) (director|manager)\b', 'Business management', 9),
    (r'\b(public works director|director of public works|county executive|city executive)\b', 'Public administration', 11),
    (r'\b(nonprofit|foundation|association) (president|director|executive)\b', 'Nonprofit leadership', 10),
]

# Specialized roles with credentials not established by the user's verified
# experience are excluded, even when titles also contain Director or VP.
SPECIALIST_EXCLUSIONS = re.compile(
    r'\b(physician|surgeon|nurse|nursing|clinical|dentist|pharmacist|attorney|'
    r'counsel|lawyer|litigation|police|sheriff|firefighter|pilot|aviation|'
    r'aerospace|spacecraft|satellite|rocket|machine learning|software engineer|'
    r'engineering director|director of engineering|security engineer|'
    r'cybersecurity|data scientist|research scientist|clinical director|'
    r'architect|electrical engineer|civil engineer|mechanical engineer|'
    r'veterinary|veterinarian|radiologist|therapist|psychologist|'
    r'professor|principal software|head of product engineering)\b', re.I)


def fetch_json(url, timeout=12):
    from source_http import fetch_json as request_json
    from public_cache import public_json
    return public_json.get(url,lambda: request_json(url,timeout))


def parse_posted_date(value):
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        try:
            n = float(value) / (1000 if float(value) > 1e11 else 1)
            return datetime.fromtimestamp(n, timezone.utc).date()
        except (ValueError, OverflowError, OSError):
            return None
    raw = str(value).strip()
    try:
        return datetime.fromisoformat(raw.replace('Z','+00:00')).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(raw).date()
    except (ValueError, TypeError, OverflowError):
        return None


def is_recent_posting(job, today=None):
    today = today or datetime.now(timezone.utc).date()
    when = parse_posted_date(job.get('date'))
    return when is not None and today - timedelta(days=MAX_POSTING_AGE_DAYS) <= when <= today


def html_to_text(value):
    # Preserve ATS <h2>/<h3> and bullet boundaries so formal qualifications
    # remain distinguishable from responsibilities and preferred experience.
    return clean_posting_text(value)


def classify_work_arrangement(location, description, declared_remote=False, declared_style='', *, cleaned=False):
    """Do not infer on-site status merely from a city or street address.

    Prefer an ATS workplace label, then a labeled work location, then explicit
    job-specific arrangement language in the advertisement. Unknown stays unknown.
    """
    description = description if cleaned else html_to_text(description)
    style = declared_arrangement(declared_style)
    if strict_onsite_requirement(description):
        return 'On-site'
    if style:
        return style
    loc=str(location or '')
    if re.search(r'\bhybrid\b',loc,re.I):
        return 'Hybrid'
    if affirmative(declared_remote):
        return 'Remote'
    if re.search(r'\b(?:fully\s+)?remote\b|\bwork from anywhere\b',loc,re.I):
        return 'Remote'
    if re.search(r'\b(?:on[- ]site|onsite|in[- ]person|office[- ]based)\b',loc,re.I):
        return 'On-site'
    return from_explicit_description(description) or 'Not specified'


def standard_job(title, company, url, location, description, source,
                 remote=False, salary='', posted=None, eligible=True, gov=False,
                 declared_style=''):
    posted_date = parse_posted_date(posted)
    if not title or not company or not isinstance(url, str) or not url.startswith('https://'):
        return None
    description = html_to_text(description)
    arrangement = classify_work_arrangement(location, description, remote, declared_style, cleaned=True)
    if explicitly_remote_title(title):
        arrangement='Remote'
    explicit_style = declared_arrangement(declared_style)
    workplace_conflict = ''
    if (strict_onsite_requirement(description)
            and explicit_style in ('Remote','Hybrid')):
        workplace_conflict = ('Provider reports '+explicit_style+
                              ', but employer posting requires in-person work.')
    arrangement_source = (
        'Explicit employer in-person requirement conflicts with provider label'
        if workplace_conflict else
        'No explicit workplace label in public posting'
        if arrangement == 'Not specified' else
        'Vacancy title explicitly states remote-only work'
        if explicitly_remote_title(title) else
        'Employer ATS workplace label' if explicit_style else
        'Provider remote flag' if affirmative(remote) else
        'Posting location or description text')
    return {
        'title': str(title).strip(), 'company': str(company).strip(),
        'employer_identity_kind': employer_identity_kind(company),
        'arrangement_source': arrangement_source,
        'workplace_conflict': workplace_conflict,
        'url': url, 'location': str(location or 'Location not specified'),
        'description': description[:26000], 'source': source,
        'description_truncated':len(description)>26000,
        'description_source':'Employer posting details as supplied by provider' if source not in ('NEOGOV','NEOED Schooljobs') else 'Provider RSS text — completeness not verified',
        'remote': arrangement == 'Remote', 'work_style': arrangement,
        'salary': str(salary or ''),
        'date': posted_date.isoformat() if posted_date else '',
        'eligible': bool(eligible), 'government': gov,
    }


def states_in_location(location):
    text = str(location or '')
    found = set()
    for code, name in US_STATES.items():
        if re.search(r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])', text, re.I):
            found.add(code)
        if re.search(r'(?:,\s*|\b)' + code + r'(?:\b|$)', text):
            found.add(code)
    return sorted(found)


def role_classification(title):
    if SPECIALIST_EXCLUSIONS.search(title or ''):
        return None
    for pattern, category, score in ROLE_PATTERNS:
        if re.search(pattern, title or '', re.I):
            return category, score
    # Adjacent roles where publisher experience transfers (sales, advertising,
    # PIO, development, chamber/tourism, production...). Base score below the
    # preset leadership titles; resume evidence decides the final order.
    family = family_for_title(title)
    if family:
        return family['label'], 10
    return None


def us_remote_eligible(raw):
    """Do not assume 'remote' means remote-from-US."""
    if isinstance(raw, list):
        if not raw:
            return True  # Provider explicitly defines empty restrictions as worldwide.
        s = ' '.join((r.get('alpha2') or r.get('name') or '') if isinstance(r,dict) else str(r) for r in raw)
    else:
        s = str(raw or '')
    return bool(re.search(r'\b(US|USA|United States|United States of America|North America|Worldwide|Anywhere|Global)\b', s, re.I))


def parse_public_rss(payload):
    """Distinguish actual RSS from an HTML block page or malformed XML."""
    prefix = payload.lstrip()[:180].lower()
    if prefix.startswith(b'<!doctype html') or prefix.startswith(b'<html') or b'<html ' in prefix:
        raise ValueError('HTML response instead of RSS; agency feed may be unavailable')
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError('Malformed RSS XML: ' + str(exc)[:80]) from exc
    tag = str(root.tag).rsplit('}', 1)[-1].lower()
    if tag not in ('rss', 'rdf', 'feed'):
        raise ValueError('Unexpected RSS response root: ' + tag[:55])
    return root


def load_neogov_feeds(state_filter=None, catalog_version=None):
    """Best-effort agency RSS. Career page URL ≠ guarantee of working RSS."""
    def one_agency(agency):
        token, employer, state = agency
        url = 'https://www.governmentjobs.com/SearchEngine/JobsFeed?' + urlencode({'agency': token})
        req = Request(url, headers={'User-Agent':'Mozilla/5.0 (personal job research)',
                                    'Accept':'application/rss+xml, application/xml, text/xml, */*'})
        jobs = []
        for item in iter_public_rss(req,timeout=12):
            def field(key):
                return (item.findtext(key) or '').strip()
            link=field('link')
            # The actual vacancy URL, not the source feed label, establishes
            # which agency is hiring. A query for Boston can return Boise.
            if not belongs_to_configured_agency(link,token,'NEOGOV'):
                continue
            job = standard_job(field('title'), employer, link,
                f'{employer}, {state}', field('description'), 'NEOGOV',
                posted=field('pubDate') or field('date'), gov=True,
                declared_style=rss_workplace_style(item))
            if job:
                job['government_agency_slug']=token
                jobs.append(job)
        return jobs, len(jobs)
    jobs, failures, counts = [], [], {}
    # All agency feeds live on one host, which slows down and times out when
    # hit with many parallel requests. Query it gently, then give feeds that
    # timed out one more try while the search still has time left.
    agencies = [a for a in GOVERNMENT_AGENCIES if state_filter is None or a[2] == state_filter]
    retry = []
    for attempt, (batch, workers) in enumerate(((agencies, 6), (retry, 3))):
        if not batch:
            continue
        with ThreadPoolExecutor(max_workers=workers) as pool:
            tasks = {pool.submit(one_agency, a): a for a in batch}
            for task in as_completed(tasks):
                agency = tasks[task]
                token, employer, state = agency
                try:
                    records, count = task.result()
                    jobs.extend(records)
                    counts[f'{employer} ({state})'] = count
                except (HTTPError, URLError, TimeoutError, ET.ParseError, ValueError, OSError) as exc:
                    timed_out = isinstance(exc, (URLError, TimeoutError, OSError)) and 'timed out' in str(exc).lower()
                    if attempt == 0 and timed_out:
                        retry.append(agency)
                        continue
                    failures.append(f'{employer} ({state}): {type(exc).__name__}: {str(exc)[:105]}')
                    counts[f'{employer} ({state})'] = 0
    return jobs, failures, counts


def load_nyc_jobs():
    """Official New York City current jobs data (public Socrata endpoint)."""
    # Server-side filtering keeps the dataset small; official post dates are used.
    where = "posting_type='External' AND (" + ' OR '.join(
        f"upper(business_title) like '%{term}%'" for term in (
            'DIRECTOR','MANAGER','ADMINISTRATOR','PUBLISHER','CHIEF OPERATING',
            'BUSINESS DEVELOPMENT','DEPUTY COMMISSIONER','EXECUTIVE')) + ')'
    params = {'$where':where, '$limit':650, '$order':'posting_date DESC'}
    raw = fetch_json('https://data.cityofnewyork.us/resource/kpav-sd4t.json?' + urlencode(params))
    jobs=[]
    for rec in raw:
        jobid = str(rec.get('job_id') or '').strip()
        if not jobid:
            continue
        # Honor a stated closing date if the Socrata row supplies one.
        deadline = parse_posted_date(rec.get('post_until'))
        if deadline and deadline < datetime.now(timezone.utc).date():
            continue
        url = 'https://cityjobs.nyc.gov/jobs'  # Generic portal; not an individual job URL.
        # The dataset's To Apply field sometimes has a specific application URL.
        apply_field = str(rec.get('to_apply') or '')
        explicit = re.search(r'https://[^\s<>"\']+', apply_field)
        if explicit:
            url = explicit.group().rstrip('.,;)')
        location = rec.get('work_location') or 'New York City, NY'
        if not states_in_location(location):
            location = str(location) + ', NY'
        salary = ''
        if rec.get('salary_range_from') and rec.get('salary_range_to'):
            salary = f"${rec['salary_range_from']}–${rec['salary_range_to']} ({rec.get('salary_frequency','')})"
        # The official NYC Open Data has SEPARATE minimum qualifications.
        # Formerly we passed only job_description, silently dropping them.
        # Keep the minimum/preferred headings so screening is transparent.
        text_blocks = [
            ('MINIMUM QUALIFICATIONS', rec.get('minimum_qual_requirements')),
            ('JOB DESCRIPTION', rec.get('job_description')),
            ('PREFERRED SKILLS', rec.get('preferred_skills')),
            ('ADDITIONAL INFORMATION', rec.get('additional_information')),
            ('HOURS AND SHIFT', rec.get('hours_shift')),
        ]
        detailed = ' '.join(
            heading + ': ' + str(value).strip()
            for heading,value in text_blocks if value)
        job = standard_job(rec.get('business_title'),
            'City of New York · ' + str(rec.get('agency') or 'City agency'),
            url, location, detailed,
            'NYC Open Data', salary=salary, posted=rec.get('posting_date'), gov=True)
        if job:
            job['reference'] = f'NYC Job ID {jobid}; search this ID at the official portal'
            job['posting_link_kind'] = ('Official NYC job directory (search by ID)' if
                                        url == 'https://cityjobs.nyc.gov/jobs'
                                        else 'URL provided in NYC application instructions')
            jobs.append(job)
    return jobs


def load_remotive():
    jobs=[]
    data=fetch_json('https://remotive.com/api/remote-jobs?limit=150')
    for x in data.get('jobs',[]):
        loc=x.get('candidate_required_location') or ''
        job=standard_job(x.get('title'), x.get('company_name'),x.get('url'),
            loc or 'Remote (location unspecified)',x.get('description'),
            'Remotive',True,x.get('salary'),x.get('publication_date'),
            eligible=us_remote_eligible(loc))
        if job: jobs.append(job)
    return jobs


def load_jobicy():
    jobs=[]
    data=fetch_json('https://jobicy.com/api/v2/remote-jobs?count=200&geo=usa')
    for x in data.get('jobs',[]):
        job=standard_job(x.get('jobTitle'),x.get('companyName'),x.get('url'),
            x.get('jobGeo') or 'USA (remote)', x.get('jobDescription'),
            'Jobicy',True,x.get('annualSalaryMin') or '',x.get('pubDate'),True)
        if job:jobs.append(job)
    return jobs


def load_himalayas(query_terms):
    # Search provider-side across several role families without excessive calls.
    # Himalayas refreshes its data daily; we cache these requests for 24 hours.
    def one_term(term):
        params=urlencode({'q':term,'country':'US','sort':'recent','page':1})
        try:
            data=fetch_json('https://himalayas.app/jobs/api/search?' + params,timeout=10)
        except (HTTPError,URLError,TimeoutError,ValueError,OSError):
            return []
        jobs=[]
        for x in data.get('jobs') or []:
            restricted=x.get('locationRestrictions')
            eligible=us_remote_eligible(restricted) if isinstance(restricted,list) else False
            loc=', '.join((r.get('name') or r.get('alpha2') or '') if isinstance(r,dict) else str(r) for r in restricted) if restricted else 'Worldwide remote'
            low,high=x.get('minSalary'),x.get('maxSalary')
            money=''
            if isinstance(low,(int,float)) and isinstance(high,(int,float)):
                money=f"{x.get('currency') or ''} {low:,.0f}–{high:,.0f} / {x.get('salaryPeriod') or 'year'}"
            job=standard_job(x.get('title'),x.get('companyName'),
                x.get('applicationLink'),loc,x.get('description') or x.get('excerpt'),
                'Himalayas',True,money,x.get('pubDate'),eligible)
            if job:jobs.append(job)
        return jobs
    results=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(one_term,t) for t in query_terms[:7]]
        for task in as_completed(futures):
            results.extend(task.result())
    return results


# Public Lever ATS boards found from actual employer career pages; no API key.
# We query only these verified employer IDs, not an imaginary cross-employer API.

def load_lever_employers(catalog_version=None):
    """Bounded Lever pagination, with transparent per-board source health.

    A 200 HTTP response with old/non-US jobs is different from a failed API
    call. Partial pages are kept when a later page fails. The public Lever
    Postings API supports mode=json, skip and limit, but no global job search.
    """
    def fetch(board):
        token,employer=board
        jobs=[]
        seen_urls=set()
        counters={'provider_records':0,'us_records':0,'dated_us':0,
                  'recent_us':0,'non_remote_recent_us':0,'pages':0}
        issue=''
        capped=False
        for offset in (0,100,200):  # maximum 300 source items per employer
            try:
                data=fetch_json('https://api.lever.co/v0/postings/' +
                    quote(token) + '?mode=json&limit=100&skip='+str(offset),
                    timeout=11)
                if not isinstance(data,list):
                    raise ValueError('Unexpected Lever JSON: expected list')
            except (HTTPError,URLError,TimeoutError,ValueError,TypeError,
                    KeyError,OSError) as exc:
                if offset==0:
                    raise
                issue=type(exc).__name__ + (
                    ' HTTP '+str(exc.code) if isinstance(exc,HTTPError) else '')
                break
            counters['pages']+=1
            counters['provider_records']+=len(data)
            new_unique=0
            for x in data:
                if not isinstance(x,dict):
                    continue
                cats=x.get('categories') or {}
                loc=cats.get('location') or ''
                style=str(x.get('workplaceType') or '')
                remote=bool(re.search(r'\bremote\b',loc,re.I)) and not declared_arrangement(style)
                eligible=bool(states_in_location(loc) or
                              re.search(r'\b(United States|USA|US)\b',loc,re.I))
                if remote and not eligible:
                    eligible=us_remote_eligible(loc)
                url=x.get('hostedUrl') or x.get('applyUrl')
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                new_unique+=1
                if eligible:
                    counters['us_records']+=1
                job=standard_job(x.get('text'),employer,url,
                    loc or 'Location not specified',
                    (x.get('descriptionPlain') or '')+' '+str(x.get('additionalPlain') or ''),
                    'Lever employer',remote,'',x.get('createdAt'),eligible,
                    declared_style=style)
                if job:
                    if eligible and job.get('date'):
                        counters['dated_us']+=1
                    if eligible and is_recent_posting(job):
                        counters['recent_us']+=1
                        if job.get('work_style')!='Remote' and not job.get('remote'):
                            counters['non_remote_recent_us']+=1
                    jobs.append(job)
            if not data or len(data)<100:
                break
            if new_unique==0:
                issue='Provider repeated a full page'
                break
            if offset==200:
                capped=True
        return jobs,{**counters,'partial_issue':issue,'truncated':capped}

    jobs,failures,health=[],[],[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(fetch,board):board for board in LEVER_BOARDS}
        for future in as_completed(futures):
            token,employer=futures[future]
            try:
                records,diag=future.result()
                jobs.extend(records)
                issue=diag['partial_issue']
                status=('Partial' if issue else
                        'Active' if diag['provider_records'] else 'Empty')
                # A provider responding with 0 valid job URLs can have
                # postings; expose this rather than mislabeling "No jobs".
                note=('No published postings' if not diag['provider_records']
                      else 'None with US location' if not diag['us_records']
                      else 'No recent US postings' if not diag['recent_us']
                      else 'Recent US vacancies available')
                if issue:
                    failures.append(employer+': partial Lever feed ('+issue+')')
                health.append({'board':employer,'feed_id':token,
                    'status':status,'records':len(records),
                    'provider_records':diag['provider_records'],
                    'us_records':diag['us_records'],
                    'recent_us':diag['recent_us'],
                    'non_remote_recent_us':diag['non_remote_recent_us'],
                    'pages':diag['pages'],'truncated':diag['truncated'],
                    'note':note,'error':issue})
            except (HTTPError,URLError,TimeoutError,ValueError,TypeError,
                    KeyError,OSError) as exc:
                error=type(exc).__name__+(
                    ' HTTP '+str(exc.code) if isinstance(exc,HTTPError) else '')
                failures.append(employer+': '+error)
                health.append({'board':employer,'feed_id':token,
                    'status':'Failed','records':0,'provider_records':None,
                    'us_records':None,'recent_us':None,
                    'non_remote_recent_us':None,'pages':0,
                    'truncated':False,'note':'Provider unavailable',
                    'error':error})
    return jobs,failures,sorted(health,key=lambda h:h['board'].casefold())


# Public job-board URLs identified on employer-hosted posting pages.
# These provider APIs are per employer: there is no universal search endpoint.
# Tokens are not guaranteed to remain active; failures appear in diagnostics.
# NEOGOV also powers education and public school districts under schooljobs.com.


# Public Workable employer job feeds. These board slugs were checked against
# public apply.workable.com career pages in October 2026; they are not a national
# Workable index, and current job availability may change.
# Curated for US non-remote leadership, publishing, distribution and management.


def load_workable_boards(catalog_version=None):
    """Official public Workable jobs endpoint; no key needed.

    Publication date comes from published_on, not last updated. Keep only jobs
    with a confirmed US location. Feed errors are surfaced under diagnostics.
    Throttle concurrency to reduce the chance of provider rate limiting.
    """
    def us_location(obj):
        if not isinstance(obj, dict):
            return False
        country = str(obj.get('country') or obj.get('country_name') or
                      obj.get('country_code') or '').strip().lower()
        return (country in ('us', 'usa', 'united states', 'united states of america')
                or bool(states_in_location(str(obj.get('state') or obj.get('state_code') or ''))))

    def fetch(board):
        token, fallback_employer = board
        payload = fetch_json('https://www.workable.com/api/accounts/' +
                             quote(token) + '?details=true', timeout=11)
        if not isinstance(payload, dict):
            raise ValueError('Workable returned an unexpected response')
        employer = str(payload.get('name') or fallback_employer)
        out = []
        for entry in payload.get('jobs') or []:
            if not isinstance(entry, dict):
                continue
            primary = {
                'city': entry.get('city'),
                'state': entry.get('state'),
                'country': entry.get('country'),
            }
            candidates = [primary] + [x for x in (entry.get('locations') or [])
                                      if isinstance(x, dict)]
            place = next((x for x in candidates if us_location(x)), None)
            if not place:
                continue
            city = str(place.get('city') or '').strip()
            state = str(place.get('state') or place.get('state_code') or '').strip()
            loc = ', '.join(p for p in (city, state, 'United States') if p)
            style = str(entry.get('workplace_type') or '').replace('_', '-')
            # Some boards include the label in a nested location object.
            if not style and isinstance(entry.get('location'), dict):
                style = str(entry['location'].get('workplace_type') or '').replace('_', '-')
            job = standard_job(
                entry.get('title'), employer,
                entry.get('url') or entry.get('shortlink') or entry.get('application_url'),
                loc,
                entry.get('description') or entry.get('full_description') or '',
                'Workable employer',
                remote=affirmative(entry.get('telecommuting')),
                posted=entry.get('published_on'), eligible=True,
                declared_style=style,
            )
            if job:
                out.append(job)
        return out
    return retrieve_boards(WORKABLE_BOARDS, fetch, max_workers=2)


def retrieve_boards(boards, worker, max_workers=8):
    """Return jobs, explicit errors AND per-board health, including empty feeds."""
    jobs, failures, health = [], [], []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        tasks={pool.submit(worker, record): record for record in boards}
        for future in as_completed(tasks):
            info=tasks[future]
            try:
                records=future.result()
                diagnostics=getattr(records,'diagnostics',{})
                jobs.extend(records)
                if diagnostics.get('failed_details') or diagnostics.get('partial_error'):
                    failures.append(f"{info[1]}: partial results; {diagnostics}")
                health.append({'board':info[1], 'feed_id':info[0],
                               'status':('Partial' if diagnostics.get('failed_details') or diagnostics.get('truncated') or diagnostics.get('partial_error') else 'Active' if records else 'Empty'),
                               'records':len(records),**diagnostics})
            except (HTTPError,URLError,TimeoutError,ValueError,TypeError,
                    KeyError,OSError) as exc:
                failures.append(f'{info[1]}: {type(exc).__name__}')
                health.append({'board':info[1], 'feed_id':info[0],
                               'status':'Failed', 'records':0,
                               'error':type(exc).__name__+': '+str(exc)[:160]})
    return jobs, failures, sorted(health,key=lambda x:(x['board'].casefold(),x['feed_id']))


def load_greenhouse_boards(catalog_version=None):
    """Greenhouse documents first_published in its public job-board API.
    Never substitute updated_at: it is not the posting date.
    """
    def fetch(board):
        token, employer=board
        data=fetch_json('https://boards-api.greenhouse.io/v1/boards/' +
                        quote(token)+'/jobs?content=true', timeout=10)
        jobs=[]
        for x in (data.get('jobs') or []):
            if not isinstance(x,dict) or x.get('internal_job_id') is None:
                continue
            location=(x.get('location') or {}).get('name') or ''
            country_ok=bool(states_in_location(location) or re.search(r'\b(United States|USA|U\.S\.)\b',location,re.I))
            if not country_ok:continue
            style = greenhouse_workplace_label(x.get('metadata'))
            job=standard_job(x.get('title'),employer,x.get('absolute_url'),location,
                x.get('content') or '','Greenhouse',
                posted=x.get('first_published'),eligible=True,
                declared_style=style)
            if job:jobs.append(job)
        return jobs
    return retrieve_boards(GREENHOUSE_BOARDS,fetch)


def load_ashby_boards(catalog_version=None):
    """Public Ashby Posting API explicitly provides publishedAt and workplaceType."""
    def fetch(board):
        token, employer=board
        data=fetch_json('https://api.ashbyhq.com/posting-api/job-board/' +
                        quote(token)+'?includeCompensation=true', timeout=10)
        jobs=[]
        for x in (data.get('jobs') or []):
            if not isinstance(x,dict) or x.get('isListed') is False:continue
            style=str(x.get('workplaceType') or '')
            provider_style=declared_arrangement(style)
            if provider_style=='Remote' or (affirmative(x.get('isRemote')) and
                                             provider_style!='Hybrid'):
                continue
            addr=((x.get('address') or {}).get('postalAddress') or {})
            region=addr.get('addressRegion') or ''
            country=str(addr.get('addressCountry') or '')
            loc=str(x.get('location') or '')
            if region and region.lower() not in loc.lower():loc=loc+', '+str(region)
            if country and country.lower() not in loc.lower():loc=loc+', '+country
            eligible=bool(states_in_location(loc) or
              re.search(r'\b(United States|USA|US)\b',loc,re.I))
            if not eligible:continue
            compensation=x.get('compensation') or {}
            pay=compensation.get('scrapeableCompensationSalarySummary') or compensation.get('compensationTierSummary') or ''
            job=standard_job(x.get('title'),employer,x.get('jobUrl') or x.get('applyUrl'),
                loc,x.get('descriptionPlain') or x.get('descriptionHtml') or '',
                'Ashby',False,pay,x.get('publishedAt'),True,
                declared_style=style)
            if job:jobs.append(job)
        return jobs
    return retrieve_boards(ASHBY_BOARDS,fetch)


def load_smartrecruiters_boards(catalog_version=None):
    """Paginated public postings with explicit partial-result diagnostics."""
    from smartrecruiters_source import fetch_board
    def fetch(board):
        return fetch_board(board,fetch_json,standard_job,role_classification,
                           parse_posted_date,MAX_POSTING_AGE_DAYS)
    return retrieve_boards(SMARTRECRUITERS_BOARDS,fetch)


def load_workday_boards(catalog_version=None):
    """Public Workday boards, searched for leadership titles (see workday_source)."""
    from workday_source import fetch_board, cache_key
    from source_http import fetch_json as request_json
    from public_cache import public_json
    def post_json(url, body):
        return public_json.get(cache_key(url, body), lambda: request_json(url, 12, body=body))
    def fetch(board):
        return fetch_board(board, post_json, fetch_json, standard_job, role_classification,
                           parse_posted_date, MAX_POSTING_AGE_DAYS, date.today())
    return retrieve_boards(WORKDAY_BOARDS, fetch, max_workers=4)


def load_schooljobs_feeds(state_filter=None, catalog_version=None):
    """NEOED schooljobs RSS, per official 2025 NEOGOV feed documentation."""
    def fetch(board):
        token,employer,state=board
        url='https://www.schooljobs.com/SearchEngine/JobsFeed?'+urlencode({'agency':token})
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 (personal job research)',
                                 'Accept':'application/rss+xml, application/xml, text/xml, */*'})
        jobs=[]
        for entry in iter_public_rss(req,timeout=12):
            f=lambda name:(entry.findtext(name) or '').strip()
            link=f('link')
            if not belongs_to_configured_agency(link,token,'NEOED Schooljobs'):
                continue
            job=standard_job(f('title'),employer,link,
                employer+', '+state,f('description'),'NEOED Schooljobs',
                posted=f('pubDate') or f('date'),gov=True,
                declared_style=rss_workplace_style(entry))
            if job:
                job['government_agency_slug']=token
                jobs.append(job)
        return jobs
    return retrieve_boards(tuple(a for a in SCHOOLJOBS_AGENCIES if state_filter is None or a[2] == state_filter),fetch)


def load_remoteok():
    jobs=[]
    raw=fetch_json('https://remoteok.com/api')
    if not isinstance(raw,list):
        return jobs
    for x in raw:
        if not isinstance(x,dict) or not x.get('position'):
            continue
        loc=x.get('location') or ''
        # Never infer US eligibility from 'remote' with no location restrictions.
        eligible=us_remote_eligible(loc)
        job=standard_job(x.get('position'),x.get('company'),x.get('url'),
            loc or 'Remote (location unknown)',x.get('description'),
            'Remote OK',True,x.get('salary') or '',x.get('date') or x.get('epoch'),eligible)
        if job:jobs.append(job)
    return jobs


def load_arbeitnow():
    jobs=[]
    for page in (1,2,3):
        raw=fetch_json(f'https://www.arbeitnow.com/api/job-board-api?page={page}')
        recs=raw.get('data') or []
        for x in recs:
            loc=str(x.get('location') or '')
            remote=bool(x.get('remote'))
            eligible=bool(states_in_location(loc) or re.search(r'\b(United States|USA|U\.S\.)\b',loc,re.I))
            if remote and not eligible:
                eligible=us_remote_eligible(loc)
            job=standard_job(x.get('title'),x.get('company_name'),x.get('url'),
                loc or 'Not specified',x.get('description'),'Arbeitnow',
                remote, '', x.get('created_at'),eligible)
            if job:jobs.append(job)
        if not recs:
            break
    return jobs


def _secret(name):
    try:
        # Streamlit 1.41 otherwise renders missing optional secrets as page errors.
        loader=getattr(type(st.secrets),'load_if_toml_exists',None)
        if loader is not None and not loader(st.secrets):
            return ''
        return str(st.secrets.get(name,'') or '').strip()
    except Exception:
        return ''


USAJOBS_DEFAULT_TERMS=('operations director','city administrator','business development',
                       'program manager','communications director')


def usajobs_terms(query_terms):
    """Search the user's keyword; fall back to career-match titles when blank."""
    typed=[str(t).strip() for t in (query_terms or ()) if str(t or '').strip()]
    return tuple(dict.fromkeys(typed))[:5] or USAJOBS_DEFAULT_TERMS


def load_usajobs_if_authorized(key, email, query_terms=()):
    # USAJOBS requires its own FREE authorization key: never try without one.
    if not key or not email:
        return []
    from source_http import fetch_json as request_json
    all_jobs=[]
    for term in usajobs_terms(query_terms):
        url='https://data.usajobs.gov/api/search?' + urlencode(
            {'Keyword':term,'ResultsPerPage':75})
        # Shared helper: retries, time budget and bounded response size.
        # Not cached, because the request carries the private API key.
        payload=request_json(url,timeout=12,headers={
            'User-Agent':email,'Authorization-Key':key})
        records=payload.get('SearchResult',{}).get('SearchResultItems',[])
        for item in records:
            x=item.get('MatchedObjectDescriptor') or {}
            det=(x.get('PositionRemuneration') or [{}])[0]
            salary=''
            if isinstance(det,dict):
                salary=str(det.get('MinimumRange',''))+'–'+str(det.get('MaximumRange',''))
            loc=' / '.join(z.get('LocationName','') for z in x.get('PositionLocation',[]) if isinstance(z,dict))
            job=standard_job(x.get('PositionTitle'),x.get('OrganizationName') or 'U.S. Government',
                x.get('PositionURI'),loc,str(x.get('UserArea',{}).get('Details',{}).get('JobSummary','')),
                'USAJOBS',False,salary,x.get('PublicationStartDate'),True,True)
            if job:all_jobs.append(job)
    return all_jobs


# Cache each upstream separately. When a feed times out, show it in diagnostics
# but do not suppress jobs from functioning sources.

def load_mayo_clinic(catalog_version=None):
    """Public Mayo Clinic career pages, limited reads; preserve feed diagnostics."""
    if not MAYO_BOARDS:
        return []
    from mayo_source import fetch_mayo_jobs
    listings = fetch_mayo_jobs()
    out = []
    for listing in listings:
        work_style = listing.get('work_style') or ''
        # Mayo Clinic alone may include fully remote positions.
        job = standard_job(listing.get('title'), 'Mayo Clinic', listing.get('url'),
            listing.get('location'), listing.get('description'), 'Mayo Clinic',
            salary=listing.get('salary'), posted=listing.get('date'),
            declared_style=work_style, eligible=True)
        if job:
            job['description_truncated']=bool(listing.get('description_truncated'))
            out.append(job)
    from source_result import SourceRecords
    return SourceRecords(out,getattr(listings,'diagnostics',{}))


def fetch_all_free_jobs(query_terms, state_filter=None, progress=None, credentials=None):
    tasks={
        'NEOGOV government': lambda: load_neogov_feeds(state_filter, SOURCE_CATALOG_VERSION),
        'NYC government': lambda: load_nyc_jobs(),
        # General remote-only providers remain excluded; Mayo Clinic is the only exception.
        'Arbeitnow': lambda: load_arbeitnow(),
        'Lever employer boards': lambda: load_lever_employers(SOURCE_CATALOG_VERSION),
        'Greenhouse public boards': lambda: load_greenhouse_boards(SOURCE_CATALOG_VERSION),
        'Ashby public boards': lambda: load_ashby_boards(SOURCE_CATALOG_VERSION),
        'SmartRecruiters public boards': lambda: load_smartrecruiters_boards(SOURCE_CATALOG_VERSION),
        'NEOED education RSS': lambda: load_schooljobs_feeds(state_filter, SOURCE_CATALOG_VERSION),
        'Workable public boards': lambda: load_workable_boards(SOURCE_CATALOG_VERSION),
        'Workday employer boards': lambda: load_workday_boards(SOURCE_CATALOG_VERSION),
        'Mayo Clinic careers': lambda: load_mayo_clinic(SOURCE_CATALOG_VERSION),
    }
    usa_key, usa_email=credentials if credentials is not None else (_secret('USAJOBS_API_KEY'),_secret('USAJOBS_EMAIL'))
    if usa_key and usa_email:
        tasks['USAJOBS']=lambda: load_usajobs_if_authorized(usa_key,usa_email,query_terms)
    jobs, errors, counts, health=[],[],{},[]
    with request_budget(90):
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures={executor.submit(fn):label for label,fn in tasks.items()}
            for future in as_completed(futures):
                label=futures[future]
                try:
                    result=future.result()
                    if label=='NEOGOV government':
                        records,failures,agency_counts=result
                        jobs.extend(records)
                        counts[label]=len(records)
                        counts['Government agency feeds in location']=sum(
                            state_filter is None or a[2] == state_filter
                            for a in GOVERNMENT_AGENCIES)
                        counts['Government agencies with RSS items']=sum(
                            n>0 for n in agency_counts.values())
                        counts['Government feeds empty']=sum(
                            n == 0 for n in agency_counts.values())-len(failures)
                        counts['Government feeds failed']=len(failures)
                        errors.extend(failures)
                        failed_names={err.split(':',1)[0].strip() for err in failures}
                        for board,number in agency_counts.items():
                            health.append({'provider':label,'board':board,
                                           'status':('Failed' if board in failed_names else
                                                     'Active' if number else 'Empty'),
                                           'records':number,
                                           'error':next((err.split(':',1)[1].strip() for err in failures if err.split(':',1)[0].strip()==board),'')})
                    elif label in ('Greenhouse public boards','Ashby public boards',
                                   'SmartRecruiters public boards','NEOED education RSS',
                                   'Workable public boards','Lever employer boards',
                                   'Workday employer boards'):
                        records,failures,board_health=result
                        jobs.extend(records)
                        counts[label]=len(records)
                        errors.extend(f'{label} / {message}' for message in failures)
                        health.extend({**x,'provider':label} for x in board_health)
                    else:
                        jobs.extend(result)
                        counts[label]=len(result)
                        diag=getattr(result,'diagnostics',{})
                        partial=bool(diag.get('failed_details') or diag.get('truncated') or diag.get('partial_error'))
                        if diag.get('failed_details') or diag.get('partial_error'):
                            errors.append(label+': partial results; '+str(diag))
                        health.append({'provider':label,'board':label,
                                       'status':'Partial' if partial else 'Active' if result else 'Empty',
                                       'records':len(result),**diag})
                except Exception as exc:
                    counts[label]=0
                    errors.append(f'{label}: {type(exc).__name__} ({str(exc)[:120]})')
                    health.append({'provider':label,'board':label,
                                   'status':'Failed','records':0,
                                   'error':type(exc).__name__+': '+str(exc)[:160]})
                check_cancelled()
                if progress:
                    progress(jobs,errors,counts,health,len(counts),len(tasks))
    return jobs,errors,counts,sorted(health,
                key=lambda x:(x['provider'],x['board'].casefold()))


def normalized_key(job):
    # A title/employer combination can represent different requisitions in
    # different cities (or in the same city). Use the actual posting identity.
    return distinct_posting_key(job)


def score_job(job, resume, words='', qualification_profile=None):
    classified=role_classification(job['title'])
    if not classified:
        # Expand beyond a preset list of publisher/director titles only when
        # several responsibility families are visible in the actual job text.
        if (not resume.strip() or SPECIALIST_EXCLUSIONS.search(job['title']) or
                len(job.get('description') or '')<300):
            return None
        description=job['description']
        transferable_clues=(
            r'\b(?:budget|forecast|profit|p\s*&\s*l)\b',
            r'\b(?:operations?|operational|process improvement|logistics|distribution)\b',
            r'\b(?:staff|employees?|workforce|personnel|team leadership)\b',
            r'\b(?:strategic|strategy|business planning)\b',
            r'\b(?:revenue|sales|marketing|business development)\b',
            r'\b(?:vendors?|contracts?|procurement|negotiat\w*)\b',
            r'\b(?:project|program|stakeholders?|community)\b',
        )
        if sum(bool(re.search(pattern,description,re.I))
               for pattern in transferable_clues)<3:
            return None
    # User's query is authoritative: title match or strongly related description.
    query_rank_bonus=0
    search_terms=[x.lower() for x in re.findall(r'[A-Za-z0-9]+',words) if len(x)>2]
    if search_terms:
        # Whole-word matching: "coo" must not match "cook", nor "art" match "start".
        def has_word(term,text):
            return re.search(r'\b'+re.escape(term)+r'\b',text) is not None
        title=job['title'].lower()
        description=job['description'].lower()
        in_title=any(has_word(w,title) for w in search_terms)
        in_description=sum(has_word(w,description) for w in search_terms)
        if not (in_title or in_description>=max(1,len(search_terms)//2)):
            return None
        query_rank_bonus+=4 if in_title else 1
    profile = qualification_profile or compile_resume_profile(
        resume, tuple(sorted(verified_competencies())))
    qualification = assess_job_qualifications(job, profile, resume)
    if classified is None:
        # A strong actual-duty match can qualify unconventional job titles.
        documented_duties=[
            item for item in qualification['resume_matches']
            if item.get('match_origin') != 'Job title only'
        ]
        if (len(documented_duties)<3 or
                qualification.get('fit_index',0)<58):
            return None
        category,score='Transferable-strength match',8
    else:
        category,score=classified
    score+=query_rank_bonus
    # Modestly boost jobs where the resume shows relevant evidence. The boost
    # is not an eligibility decision or a hiring-success probability.
    score += qualification['rank_bonus']
    competencies = ([x['area'] for x in qualification['resume_matches']]
                    + [x['area'] for x in qualification['confirmed_only']])[:5]
    if job['government']:
        score += 1
    return {**job, 'category':category, 'rank':score,
            'competency_hits':competencies, 'qualification_match':qualification,
            'evidence_index':evidence_index(qualification),
            'states':states_in_location(job['location'])}


def filter_and_rank_jobs(jobs, state_code, work_style, query, resume,
                         max_per_employer=None, preferences=None,
                         listing_scope='Direct employers only (recommended)',
                         confirmed=None, scoring_cache=None, excluded=()):
    from source_http import check_cancelled
    import hashlib,json
    confirmed_areas = tuple(sorted(verified_competencies() if confirmed is None else confirmed))
    exclusions = tuple(sorted(excluded or ()))
    qualification_profile = (compile_resume_profile(resume, confirmed_areas, exclusions)
                             if exclusions else compile_resume_profile(resume, confirmed_areas))
    unique={}
    excluded={'old':0,'undated':0,'eligibility':0,'irrelevant':0,
              'location':0,'employer_limit':0,'preferences':0,
              'recruiter':0,'directory_link':0,'indirect_source':0,
              'foreign_location':0}
    for cached_job in dedupe_vacancy_urls(jobs):
        check_cancelled()
        # Cached provider entries may predate the latest work-style parser.
        # Repair inconsistent provenance before screening and exporting.
        job=reconcile_workplace_record(cached_job)
        # Revalidate already-cached government records as well; imported
        # data from earlier releases may have incorrect agency labels.
        if job.get('source') in ('NEOGOV','NEOED Schooljobs'):
            catalog=(GOVERNMENT_AGENCIES if job['source']=='NEOGOV'
                     else SCHOOLJOBS_AGENCIES)
            if not any(job.get('company')==name and
                       belongs_to_configured_agency(
                           job.get('url'),slug,job.get('source'))
                       for slug,name,_state in catalog):
                excluded['eligibility']+=1
                continue
        if not job.get('date'):
            excluded['undated']+=1
            continue
        if not is_recent_posting(job):
            excluded['old']+=1
            continue
        if not job.get('eligible'):
            excluded['eligibility']+=1
            continue
        if 'spacex' in job['company'].casefold():
            continue
        # Remote exceptions are Mayo Clinic and verified government
        # postings. On-site-only and Hybrid-only filters remain strict.
        # Unknown workplaces remain labeled for verification.
        arrangement=job.get('work_style') or (
            'Remote' if job.get('remote') else 'Not specified')
        # Cached provider records also need title-based remote screening;
        # a vacancy named "(Remote)" isn't work-style unspecified.
        if explicitly_remote_title(job.get('title')):
            arrangement='Remote'
            job['work_style']='Remote'
            job['remote']=True
            job['arrangement_source']='Vacancy title explicitly states remote-only work'
        if arrangement == 'Remote' and not permitted_remote_source(job):
            excluded['location']+=1
            continue
        quality=posting_quality(job)
        if quality['foreign_location']:
            excluded['foreign_location']+=1
            continue
        if listing_scope != 'All sources (including directory links)':
            if not quality['individual_url']:
                excluded['directory_link']+=1
                continue
            if not quality['direct_source']:
                excluded['indirect_source']+=1
                continue
            if (listing_scope == 'Direct employers only (recommended)'
                    and quality['recruiter']):
                excluded['recruiter']+=1
                continue
        if work_style == 'On-site only' and arrangement != 'On-site':
            excluded['location']+=1
            continue
        if work_style == 'Hybrid only' and arrangement != 'Hybrid':
            excluded['location']+=1
            continue
        state_ids=states_in_location(job['location'])
        if state_code and state_code not in state_ids:
            excluded['location']+=1
            continue
        if not preferences_allow(job,state_ids,preferences):
            excluded['preferences']+=1
            continue
        cache_key=hashlib.sha256(json.dumps(job,sort_keys=True,default=str).encode()).hexdigest()
        if scoring_cache is not None and cache_key in scoring_cache:
            ranked=scoring_cache[cache_key]
        else:
            ranked=score_job(job,resume,query,qualification_profile)
            if scoring_cache is not None: scoring_cache[cache_key]=ranked
        if ranked is None:
            excluded['irrelevant']+=1
            continue
        key=normalized_key(job)
        # Keep the stronger *qualification* match when multiple feeds list
        # the same title and employer, instead of using broad title rank only.
        if (key not in unique or
                (ranked['evidence_index'], ranked['rank']) >
                (unique[key]['evidence_index'], unique[key]['rank'])):
            unique[key]=ranked
    # With an uploaded resume, strict descending *documented qualification*
    # overlap takes priority over titles, provider familiarity and posting date.
    # Without a resume, preserve the existing title/relevance ranking.
    if resume.strip():
        sorted_jobs=sorted(unique.values(),key=lambda job: career_sort_key(job,evidence_sort_key))
    else:
        sorted_jobs=sorted(unique.values(),key=lambda j:(
            -j['rank'],-int(j['date'].replace('-','')),j['title'].lower()))
    # Default: show ALL qualifying jobs in strict match order, including
    # employers with many openings. The optional compact view retains the
    # previous three-per-employer cap (up to 10 for Mayo Clinic).
    company_counts=Counter()
    diverse=[]
    for job in sorted_jobs:
        company=job['company'].strip().casefold()
        cap=(10 if company=='mayo clinic' else max_per_employer)
        if max_per_employer is not None and company_counts[company]>=cap:
            excluded['employer_limit']+=1
            continue
        company_counts[company]+=1
        diverse.append(job)
    if resume.strip():
        # No sector interleaving: that would break best-to-worst ordering.
        return diverse, excluded
    # Preserve previous government/private variety when a resume isn't loaded.
    government=[j for j in diverse if j['government']]
    private=[j for j in diverse if not j['government']]
    interleaved=[]
    while government or private:
        if government: interleaved.append(government.pop(0))
        if private: interleaved.append(private.pop(0))
        if private: interleaved.append(private.pop(0))
    return interleaved,excluded


def save_result_to_tracker(job):
    identity=posting_id(job)
    if any(posting_id({'company':x['Company'],'title':x['Job Title'],
                       'url':x['Job URL'],'location':x['Location']})==identity
           for x in st.session_state.jobs):
        return False
    st.session_state.jobs.append({
        'Company':job['company'],'Job Title':job['title'],
        'Location':job['location'],'Job URL':job['url'],
        'Salary':job['salary'],'Status':'Saved','Date Recorded':str(date.today()),
        'Interview Date':'','Follow-up Date':'','Notes':f"Source: {job['source']}; review qualifications and original posting before applying."})
    persist_tracker_if_unlocked()
    return True
def tracker_cloud_enabled():
    return bool(_secret('TRACKER_DATABASE_URL') and _secret('TRACKER_ACCESS_PASSWORD'))


def persist_tracker_if_unlocked():
    return tracker_sync.persist(st.session_state,_secret('TRACKER_DATABASE_URL'),
        _secret('TRACKER_WORKSPACE_ID') or 'personal',tracker_cloud_enabled())


def unlock_tracker_workspace(password):
    from tracker_store import unlock_throttle
    if unlock_throttle.seconds_remaining():
        return False
    accepted=authenticate(password,_secret('TRACKER_ACCESS_PASSWORD'))
    unlock_throttle.record(accepted)
    if not accepted:
        return False
    remote=load_remote_workspace(
        _secret('TRACKER_DATABASE_URL'),
        _secret('TRACKER_WORKSPACE_ID') or 'personal')
    conflicts=tracker_sync.adopt_remote(st.session_state,remote)
    if not conflicts:
        persist_tracker_if_unlocked()

    return True


def search_fingerprint():
    return hashlib.sha256(json.dumps([MATCHING_ENGINE_VERSION,st.session_state.resume_text,
        sorted(verified_competencies()),sorted(excluded_competencies())]).encode()).hexdigest()


def run_search_task(task,settings):
    """All inputs are captured on the UI thread; no session state in workers."""
    import time as _time
    cache={}
    started=_time.monotonic()
    timing={'source_done':{},'rank_seconds':0.0,'rank_calls':0}
    base={'preferences':settings['preferences'],'run_id':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
          'matching_version':MATCHING_ENGINE_VERSION,'scope':settings['scope'],
          'work':settings['work'],'listing_scope':settings['listing_scope'],
          'employer_scope':settings['employer_scope'],'searched':datetime.now().strftime('%b %d, %Y %I:%M %p')}
    def rank(raw):
        t=_time.monotonic()
        try:
            return _rank(raw)
        finally:
            timing['rank_seconds']+=_time.monotonic()-t
            timing['rank_calls']+=1
    def _rank(raw):
        return filter_and_rank_jobs(raw,settings['code'],settings['work'],settings['query'],
            settings['resume'],settings['employer_cap'],settings['preferences'],
            settings['listing_scope'],confirmed=settings['confirmed'],scoring_cache=cache,
            excluded=settings.get('excluded',()))
    def publish(raw,errors,counts,health,completed=0,total=0,bulletin=None):
        for label in counts:
            timing['source_done'].setdefault(label,round(_time.monotonic()-started,1))
        matches,excluded=rank(raw)
        readiness=settings.get('family_readiness') or {}
        for job in matches:
            family=family_for_title(job.get('title'))
            job['role_family']=family['label'] if family else ''
            job['family_readiness']=readiness.get(job['role_family'])
        bulletin=dict(bulletin or {})
        if bulletin:
            bulletin['summary_only_fetched']=bulletin.get('summary_only',0)
            bulletin['summary_only']=sum(x.get('description_source','').startswith('RSS summary') for x in matches)
        stats={**base,'fetched':len(raw),'sources':dict(counts),'errors':list(errors),
            'board_health':with_recovery_links(health),'excluded':excluded,'new_count':0,'had_baseline':False,
            'government':sum(bool(x['government']) for x in matches),
            'bulletin_diagnostics':bulletin or {},'search_status':'running',
            'timing':{**timing,'rank_seconds':round(timing['rank_seconds'],1),
                      'elapsed':round(_time.monotonic()-started,1)}}
        task.publish({'matches':matches,'stats':stats},
            f'{len(health)} sources reported · {len(matches)} matches so far')
    raw,errors,counts,health=fetch_all_free_jobs((settings['query'],),settings['code'],
        progress=publish,credentials=settings['credentials'])
    timing['fetch_done']=round(_time.monotonic()-started,1)
    if settings['resume'].strip():
        task.publish(message='Checking full government descriptions; current results remain available')
        preview,_=rank(raw)
        t=_time.monotonic()
        raw,bulletin=enrich_priority_government_jobs(raw,preview,limit=40)
        timing['bulletin_seconds']=round(_time.monotonic()-t,1)
    else: bulletin={}
    publish(raw,errors,counts,health,bulletin=bulletin)


def consume_search_update():
    task=st.session_state.get('active_search')
    if task is None: return
    if task.fingerprint!=search_fingerprint():
        task.cancel()
        del st.session_state['active_search']
        return
    if task.snapshot(False)['revision']==st.session_state.get('search_task_revision'): return
    snap=task.snapshot()
    st.session_state.search_task_revision=snap['revision']
    payload=snap['payload']
    if payload is None: return # Keep the previous search if none completed.
    matches=payload['matches']; stats=payload['stats']
    terminal=snap['status']!='running'
    matches,new_seen=annotate_new_results(matches,st.session_state.seen_jobs,st.session_state.search_baseline)
    stats.update(search_status=snap['status'],elapsed_seconds=snap['elapsed'],
        first_results_seconds=snap.get('first_results_seconds'),
        had_baseline=st.session_state.search_baseline,
        new_count=sum(bool(x['new_since_last_search']) for x in matches))
    if terminal:
        st.session_state.seen_jobs=new_seen
        st.session_state.search_baseline=True
        persist_tracker_if_unlocked()
    st.session_state.search_results=matches
    st.session_state.search_stats=stats
    # The page is reset when a new search starts, not on each partial update,
    # so browsing results while sources finish does not jump back to page 1.


@st.fragment(run_every=1)
def render_search_progress():
    task=st.session_state.get('active_search')
    if task is None: return
    snap=task.snapshot(False)
    if snap['revision']!=st.session_state.get('search_task_revision') and st.session_state.get('top_navigation')=='Find Jobs':
        st.rerun()
    if snap['status']=='running':
        st.info(f"{snap['message']} · {int(snap['elapsed'])} seconds. You can use other pages while this search runs.")
        if st.button('Stop search',key='cancel_search'):
            task.cancel()
        if task.cancel_event.is_set():
            st.caption('Stopping outstanding requests; completed results will remain available.')
    elif snap['status']!='complete':
        st.warning(snap['message'])
    else:
        st.caption(f"Search complete · {snap['elapsed']} seconds · Results available in Find Jobs")
