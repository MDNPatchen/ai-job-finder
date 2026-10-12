import re
import json
import html
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from io import BytesIO
from datetime import date
import streamlit as st
import fitz
from docx import Document
import pandas as pd

st.set_page_config(page_title='AI Job Finder', page_icon='💼', layout='wide')

SKILLS = ['Leadership','Strategic Planning','Marketing','Data Analysis','Logistics','Compliance','Project Management','Operations Management','Budget Management','P&L Management','Advertising Sales','Digital Strategy','Audience Development','Community Relations','Business Development','Team Management','Revenue Growth','Financial Planning','Change Management','Circulation','Editorial Leadership','Sales Management','Vendor Management']
TITLES = ['Group Newspaper Publisher','Group Publisher','Newspaper Publisher','Publisher','Operations Director','Director of Operations','General Manager','Regional Manager','Operations Manager','Project Manager','Sales Director','Vice President']
STATUSES = ['Saved','Applied','Interviewing','Offer','Rejected','Skipped','Withdrawn']
PUBLISHER_AREAS = ['Multi-publication or multi-site leadership','Revenue, profitability, and P&L oversight','Advertising and sales leadership','Digital publishing and subscriptions','Editorial and cross-functional leadership','Budgeting, forecasting, and financial planning','Audience growth and marketing','Community and advertiser partnerships','Circulation, distribution, and logistics','Talent development and organizational change']

# These eight responsibilities were explicitly confirmed by the user.
# They remain editable; session state is not permanent storage.
VERIFICATION_AREAS = {
    'Full profit-and-loss (P&L) responsibility': 'Financial & P&L leadership',
    'Managing multiple business locations or publications': 'Multi-site business leadership',
    'Hiring, supervising, and developing department managers': 'Talent & organizational change',
    'Negotiating major contracts and vendor agreements': 'Negotiation & vendor management',
    'Developing annual budgets and financial forecasts': 'Financial & P&L leadership',
    'Leading revenue growth and business transformation': 'Revenue growth & transformation',
    'Overseeing distribution and logistics operations': 'Distribution & logistics',
    'Managing digital products and revenue': 'Digital transformation',
}
INITIAL_VERIFIED = list(VERIFICATION_AREAS)

for key, default in {'jobs': [], 'resume_text': '', 'confirmed_titles': [], 'analysis': None,
                     'approved_suggestions': [], 'verified_duties': INITIAL_VERIFIED.copy()}.items():
    if key not in st.session_state:
        st.session_state[key] = default


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


def keyword_matches(text, options):
    return [item for item in options if re.search(r'\b' + re.escape(item) + r'\b', text, re.I)]


# A local, transparent reference library. These are examples of common publisher
# responsibilities, not assertions about the user's actual experience.
COMPETENCIES = [
    ('Financial & P&L leadership', ['profitability', 'profit and loss', 'p&l', 'budget', 'forecast', 'cash flow', 'financial performance'], 'Financial leadership', 'Regional General Manager'),
    ('Multi-site business leadership', ['multiple newspapers', 'multiple publications', 'group publisher', 'group newspaper publisher', 'multi-site', 'multi-location', 'regional operations'], 'Multi-location leadership', 'Regional Operations Director'),
    ('Revenue growth & transformation', ['revenue growth', 'revenue increase', 'business transformation', 'turnaround', 'restructur', 'growth strategy'], 'Revenue and change leadership', 'General Manager'),
    ('Advertising & sales leadership', ['advertising', 'ad sales', 'sales team', 'sales director', 'sales revenue', 'account executives'], 'Commercial leadership', 'Director of Sales'),
    ('Digital transformation', ['digital revenue', 'digital marketing', 'online advertising', 'digital subscription', 'digital strategy', 'website'], 'Digital business growth', 'Digital Strategy Director'),
    ('Editorial & cross-functional leadership', ['editorial', 'managing editor', 'newsroom', 'editor', 'cross-functional'], 'Cross-functional management', 'General Manager'),
    ('Audience & marketing development', ['circulation', 'audience', 'subscriber', 'subscription', 'marketing', 'readership'], 'Customer growth', 'Marketing Director'),
    ('Distribution & logistics', ['distribution', 'delivery', 'route', 'logistics', 'circulation director'], 'Operations optimization', 'Distribution Director'),
    ('Talent & organizational change', ['recruit', 'hiring', 'training', 'cross-training', 'reorganization', 'staff development', 'employee'], 'People leadership', 'Director of Operations'),
    ('Community partnerships', ['community', 'chamber', 'partnership', 'advertiser relationships', 'stakeholder'], 'Stakeholder relations', 'Community Relations Director'),
    ('Negotiation & vendor management', ['negotiat', 'vendor', 'contract', 'supplier', 'insurance premium'], 'Negotiation', 'Procurement Director'),
]


def analyze_locally(resume):
    lines = [line.strip() for line in resume.splitlines() if line.strip()]
    documented, verify, roles, suggestions = [], [], {}, []
    for skill, phrases, transferable, role in COMPETENCIES:
        evidence = []
        for line in lines:
            if any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', line, re.I) for term in phrases):
                evidence.append(line[:350])
            if len(evidence) == 2:
                break
        if evidence:
            documented.append({'skill': skill, 'evidence': evidence, 'transferable': transferable})
            roles.setdefault(role, []).append(transferable)
            suggestions.append({'skill': skill, 'source': evidence[0],
                'wording': f'Experience in {transferable.lower()}: {evidence[0]}',
                'note': 'Draft based on resume wording; edit for accuracy before using.'})
        else:
            verify.append(skill)
    return {'documented': documented, 'verify': verify, 'roles': roles, 'suggestions': suggestions}

# Career matches use the same publisher competency evidence as Career Analysis.
# Scores are transparent overlap indicators, not employment eligibility predictions.
CAREER_PATHS = [
    {'title': 'Regional Operations Director', 'industry': 'Multi-location businesses', 'core': ['Multi-site business leadership', 'Financial & P&L leadership', 'Talent & organizational change'], 'additional': ['Distribution & logistics', 'Negotiation & vendor management'], 'focus': 'Emphasize locations led, budgets, operational improvements and team size.'},
    {'title': 'General Manager', 'industry': 'Services, media, retail and local businesses', 'core': ['Financial & P&L leadership', 'Advertising & sales leadership', 'Talent & organizational change'], 'additional': ['Multi-site business leadership', 'Revenue growth & transformation'], 'focus': 'Highlight overall business ownership, revenue, profitability and leadership results.'},
    {'title': 'Director of Business Development', 'industry': 'Business services and B2B organizations', 'core': ['Advertising & sales leadership', 'Community partnerships', 'Financial & P&L leadership'], 'additional': ['Revenue growth & transformation', 'Negotiation & vendor management'], 'focus': 'Show account growth, partnerships, pricing strategy and measurable sales outcomes.'},
    {'title': 'Director of Marketing', 'industry': 'Marketing, media and consumer services', 'core': ['Audience & marketing development', 'Digital transformation', 'Advertising & sales leadership'], 'additional': ['Community partnerships', 'Financial & P&L leadership'], 'focus': 'Show audience growth, campaign results, digital revenue and customer acquisition.'},
    {'title': 'Distribution Operations Director', 'industry': 'Logistics and delivery services', 'core': ['Distribution & logistics', 'Talent & organizational change', 'Financial & P&L leadership'], 'additional': ['Multi-site business leadership', 'Negotiation & vendor management'], 'focus': 'Show delivery efficiencies, route changes, service levels and cost savings.'},
    {'title': 'Director of Community Partnerships', 'industry': 'Nonprofits, education and civic organizations', 'core': ['Community partnerships', 'Talent & organizational change', 'Audience & marketing development'], 'additional': ['Advertising & sales leadership', 'Financial & P&L leadership'], 'focus': 'Describe stakeholder relationships, public-facing leadership and partnership outcomes.'},
    {'title': 'Digital Business Director', 'industry': 'Digital media and subscription businesses', 'core': ['Digital transformation', 'Audience & marketing development', 'Financial & P&L leadership'], 'additional': ['Advertising & sales leadership', 'Editorial & cross-functional leadership'], 'focus': 'Show digital product initiatives, subscription or advertising growth, and cross-team execution.'},
    {'title': 'Chief Operating Officer (smaller organization)', 'industry': 'Small and midsize organizations', 'core': ['Financial & P&L leadership', 'Multi-site business leadership', 'Talent & organizational change'], 'additional': ['Negotiation & vendor management', 'Revenue growth & transformation'], 'focus': 'Document executive decision-making, business scale, direct reports and financial accountability.'},
]


def verified_competencies():
    return set(VERIFICATION_AREAS[duty] for duty in st.session_state.verified_duties)


def verification_editor():
    st.subheader('Experience Verification')
    st.write('These eight publisher responsibilities were preselected because you confirmed them. '
             'Uncheck anything you want to remove. Changes affect career matching immediately.')
    with st.form('experience_verification_form'):
        selected = []
        for duty in VERIFICATION_AREAS:
            if st.checkbox(duty, value=duty in st.session_state.verified_duties, key='verify_' + str(list(VERIFICATION_AREAS).index(duty))):
                selected.append(duty)
        if st.form_submit_button('Save verified experience'):
            st.session_state.verified_duties = selected
            st.session_state.pop('career_matches', None)
            st.success('Verified responsibilities updated for this session.')
    st.caption('Confirmed experience is based on your approval, not inferred from keywords. '
               'It is not automatically added to your resume.')


def get_career_matches(resume):
    analysis = analyze_locally(resume)
    evidence_by_skill = {item['skill']: item['evidence'] for item in analysis['documented']}
    verified = verified_competencies()
    results = []
    for path in CAREER_PATHS:
        all_skills = path['core'] + path['additional']
        matched = [skill for skill in all_skills if skill in evidence_by_skill or skill in verified]
        unconfirmed = [skill for skill in all_skills if skill not in matched]
        # Core requirements count twice as much as additional competencies.
        total_weight = 2 * len(path['core']) + len(path['additional'])
        matched_weight = sum(2 if skill in path['core'] else 1 for skill in matched)
        score = round(100 * matched_weight / total_weight)
        results.append({**path, 'score': score, 'matched': matched,
                        'unconfirmed': unconfirmed, 'evidence': evidence_by_skill,
                        'verified': [skill for skill in matched if skill in verified]})
    return sorted(results, key=lambda x: (-x['score'], x['title']))


# Free public remote-job feeds. Cache requests to avoid unnecessary provider traffic.
# Search APIs query the provider directly, rather than filtering only a small
# downloaded feed. Listings must be independently checked before applying.
SEARCH_TERMS = [
    'operations', 'business development', 'general manager', 'marketing',
    'partnerships', 'logistics', 'chief operating officer', 'publisher'
]


def fetch_json(url):
    request = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; PersonalCareerResearch/1.0)',
        'Accept': 'application/json'})
    with urlopen(request, timeout=16) as response:
        return json.load(response)


def standard_job(title, company, url, location, description, source,
                 remote=True, salary='', posted='', eligible=True):
    if not (title and company and str(url).startswith('https://')):
        return None
    return {'title': str(title).strip(), 'company': str(company).strip(),
            'url': str(url), 'location': str(location or 'Not specified'),
            'remote': bool(remote), 'salary': str(salary or ''),
            'date': str(posted or '')[:10],
            'description': html_to_text(str(description or ''))[:6000],
            'source': source, 'eligible': eligible}


@st.cache_data(ttl=3600, show_spinner=False)
def load_public_jobs():
    jobs, errors, counts = [], [], {}
    # Jobicy publishes recent remote jobs. Its USA filter is supplied by Jobicy.
    try:
        payload = fetch_json('https://jobicy.com/api/v2/remote-jobs?count=200&geo=usa')
        for rec in payload.get('jobs', []):
            job = standard_job(rec.get('jobTitle'), rec.get('companyName'),
                rec.get('url'), rec.get('jobGeo') or 'USA / Remote',
                rec.get('jobDescription'), 'Jobicy', True,
                rec.get('annualSalaryMin') or '', rec.get('pubDate'), True)
            if job: jobs.append(job)
        counts['Jobicy'] = len([j for j in jobs if j['source'] == 'Jobicy'])
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, TypeError) as exc:
        errors.append(f'Jobicy could not be loaded ({type(exc).__name__}).')

    # Himalayas searches remotely hosted jobs by keyword and country. Searching
    # provider-side prevents executive titles from being lost in feed sampling.
    for term in SEARCH_TERMS:
        try:
            url = 'https://himalayas.app/jobs/api/search?' + urlencode(
                {'q': term, 'country': 'US', 'sort': 'recent', 'page': 1})
            payload = fetch_json(url)
            for rec in payload.get('jobs', []):
                restrictions = rec.get('locationRestrictions') or []
                location = ', '.join(str(x) for x in restrictions) if restrictions else 'Worldwide / Remote'
                low, high, currency = rec.get('minSalary'), rec.get('maxSalary'), rec.get('currency') or ''
                salary = f'{currency} {low:,}–{high:,} / {rec.get("salaryPeriod") or "year"}' if isinstance(low, (int,float)) and isinstance(high,(int,float)) else ''
                job = standard_job(rec.get('title'), rec.get('companyName'),
                    rec.get('applicationLink'), location,
                    rec.get('description') or rec.get('excerpt'), 'Himalayas',
                    True, salary, rec.get('pubDate'), True)
                if job: jobs.append(job)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, TypeError) as exc:
            errors.append(f'Himalayas search for {term} failed ({type(exc).__name__}).')
    counts['Himalayas'] = len([j for j in jobs if j['source'] == 'Himalayas'])

    # Remotive supplements those sources. Location restrictions are interpreted
    # conservatively, rather than assuming every remote job accepts U.S. applicants.
    try:
        payload = fetch_json('https://remotive.com/api/remote-jobs')
        for rec in payload.get('jobs', []):
            location = str(rec.get('candidate_required_location') or 'Unspecified')
            eligible = any(x in location.lower() for x in
                ['usa', 'united states', 'u.s.', 'north america', 'worldwide', 'anywhere', 'global'])
            job = standard_job(rec.get('title'), rec.get('company_name'),
                rec.get('url'), location, rec.get('description'), 'Remotive',
                True, rec.get('salary'), rec.get('publication_date'), eligible)
            if job: jobs.append(job)
        counts['Remotive'] = len([j for j in jobs if j['source'] == 'Remotive'])
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, TypeError) as exc:
        errors.append(f'Remotive could not be loaded ({type(exc).__name__}).')
    unique = {}
    for job in jobs:
        unique.setdefault(job['url'].split('?')[0], job)
    return list(unique.values()), errors, counts

def html_to_text(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value))).strip()


def us_eligible(job):
    return bool(job.get('eligible', False))


ROLE_ALIASES = {
    'Chief Operating Officer (smaller organization)': ['chief operating officer', 'coo', 'head of operations', 'vp operations', 'vice president operations'],
    'Distribution Operations Director': ['distribution director', 'director of distribution', 'logistics director', 'director of logistics', 'supply chain director'],
    'Regional Operations Director': ['regional operations', 'regional director', 'director of operations', 'operations director', 'area manager'],
    'Digital Business Director': ['digital director', 'director of digital', 'digital business', 'digital strategy director', 'digital operations'],
    'Director of Community Partnerships': ['partnerships director', 'director of partnerships', 'community relations director', 'community engagement director'],
    'Director of Business Development': ['business development director', 'director of business development', 'head of business development', 'commercial director'],
    'Director of Marketing': ['marketing director', 'director of marketing', 'head of marketing'],
    'General Manager': ['general manager', 'business unit manager', 'managing director'],
}


def role_similarity(title, role):
    value = re.sub(r'[^a-z0-9 ]', ' ', title.lower())
    value = re.sub(r'\s+', ' ', value).strip()
    aliases = ROLE_ALIASES.get(role, [role.lower()])
    for phrase in aliases:
        clean = re.sub(r'[^a-z0-9 ]', ' ', phrase.lower())
        clean = re.sub(r'\s+', ' ', clean).strip()
        if re.search(r'\b' + re.escape(clean) + r'\b', value):
            return 3
    # Broader but still meaningful leadership-title signals.
    if role in ['Regional Operations Director', 'Distribution Operations Director'] and 'operations' in value and any(t in value for t in ['director', 'head', 'vp']):
        return 1
    return 0


def job_competency_hits(job, resume):
    # Uses verified experience or phrases in the resume; compares to job description.
    confirmed = verified_competencies()
    if resume.strip():
        confirmed |= {item['skill'] for item in analyze_locally(resume)['documented']}
    job_text = job['title'] + ' ' + job['description']
    matches = []
    for area, phrases, *_ in COMPETENCIES:
        if area in confirmed and any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', job_text, re.I) for term in phrases):
            matches.append(area)
    return matches[:5]


st.sidebar.title('💼 AI Job Finder')
page = st.sidebar.radio('Navigation', ['Dashboard','My Resume','Career Analysis','Career Matches','Find Jobs','Job Tracker'])
st.sidebar.caption('Free local resume comparison. No API key or AI usage charges.')

if page == 'Dashboard':
    st.title('📊 Job Search Dashboard')
    jobs = st.session_state.jobs
    a, b, c = st.columns(3)
    a.metric('Tracked Jobs', len(jobs))
    b.metric('Applied', sum(j['Status'] == 'Applied' for j in jobs))
    c.metric('Interviewing', sum(j['Status'] == 'Interviewing' for j in jobs))
    a, b, c = st.columns(3)
    a.metric('Offers', sum(j['Status'] == 'Offer' for j in jobs))
    b.metric('Saved', sum(j['Status'] == 'Saved' for j in jobs))
    c.metric('Skipped', sum(j['Status'] == 'Skipped' for j in jobs))
    if jobs:
        st.dataframe(pd.DataFrame(jobs), use_container_width=True, hide_index=True)
    else:
        st.info('Go to Job Tracker to add a job.')
    st.caption('Jobs are stored only for this session. Export your CSV to keep a backup.')

elif page == 'My Resume':
    st.title('📄 My Resume')
    file = st.file_uploader('Upload PDF, Word, or TXT resume', type=['pdf','docx','txt'])
    if file:
        try:
            extracted = extract_resume_text(file)
            if extracted.strip():
                if extracted != st.session_state.resume_text:
                    st.session_state.resume_text = extracted
                    st.session_state.analysis = None
                    st.session_state.pop('career_matches', None)
                    st.session_state.approved_suggestions = []
                st.success('Resume uploaded successfully!')
            else:
                st.warning('No readable text was found. Scanned PDFs may need OCR.')
        except Exception as exc:
            st.error(f'Unable to read file: {exc}')
    text = st.session_state.resume_text
    if text:
        with st.expander('View extracted resume text'):
            st.text_area('Resume text', text, height=280)
        st.subheader('Skills mentioned in your resume')
        matches = keyword_matches(text, SKILLS)
        st.write(', '.join(matches) if matches else 'No matches from the starter list.')
        st.caption('These are keyword matches, not verified skill assessments.')
        st.subheader('Confirm your actual job titles')
        found = keyword_matches(text, TITLES)
        if not st.session_state.confirmed_titles:
            st.session_state.confirmed_titles = ['Group Newspaper Publisher']
        choices = list(dict.fromkeys(found + st.session_state.confirmed_titles))
        selected = st.multiselect('Recognized or previously confirmed titles', choices, default=[t for t in st.session_state.confirmed_titles if t in choices])
        additional = st.text_input('Add other actual titles (comma-separated)')
        confirmed = list(dict.fromkeys(selected + [x.strip() for x in additional.split(',') if x.strip()]))
        st.session_state.confirmed_titles = confirmed
        st.write('**Confirmed titles:**', ', '.join(confirmed) if confirmed else 'None yet')
        st.info('Next, open Career Analysis to compare your experience against publisher responsibilities.')
    else:
        st.info('Upload a resume to begin.')

elif page == 'Career Analysis':
    st.title('🧭 Publisher Competency & Transferable Skills')
    st.write('Free, local comparison of your resume with common Group Newspaper Publisher responsibilities. Nothing is sent to an AI service.')
    actual_title = st.text_input('Your actual position', value='Group Newspaper Publisher')
    st.caption('Your real job title stays separate from transferable job categories.')
    verification_editor()
    if not st.session_state.resume_text:
        st.warning('First upload your resume on the My Resume page.')
    else:
        if st.button('Analyze My Resume', type='primary'):
            st.session_state.analysis = analyze_locally(st.session_state.resume_text)
            st.session_state.approved_suggestions = []
            st.success('Comparison complete. Review each result for accuracy.')
        analysis = st.session_state.analysis
        if analysis:
            st.subheader('Possible documented strengths')
            st.caption('A matching phrase is a clue, not proof you performed the duty. Review the source text.')
            for item in analysis['documented']:
                with st.expander(item['skill'], expanded=False):
                    st.write('**Resume text that matched:**')
                    for line in item['evidence']:
                        st.write(line)
                    st.write('**Transferable area:**', item['transferable'])
            st.subheader('Confirmed experience not necessarily documented in the resume')
            documented_skills = {item['skill'] for item in analysis['documented']}
            for duty in st.session_state.verified_duties:
                area = VERIFICATION_AREAS[duty]
                if area not in documented_skills:
                    st.write('✓ ' + duty + ' — **confirmed by you; add supporting details to your resume**')
            st.subheader('Other publisher competencies to investigate')
            missing = [area for area in analysis['verify'] if area not in verified_competencies()]
            if missing:
                for area in missing:
                    st.write('• ' + area)
            else:
                st.write('No additional competencies missing from this starter library.')
            st.subheader('Potential related career paths')
            for role, skills in analysis['roles'].items():
                st.write(f'**{role}** — related experience: {", ".join(skills)}')
            st.caption('These are ideas for exploration, not eligibility or job-match guarantees.')
            st.subheader('Draft wording for confirmed experience')
            st.caption('These are responsibility statements, not achievement claims. Add real scale, outcomes, and numbers only when accurate.')
            verified_drafts = []
            for i, duty in enumerate(st.session_state.verified_duties):
                proposed = st.text_area('Draft for: ' + duty,
                    value=duty.rstrip('.') + '.', key='verified_draft_' + str(i))
                if st.checkbox('Approve verified responsibility ' + str(i + 1), key='verified_approve_' + str(i)) and proposed.strip():
                    verified_drafts.append(proposed.strip())
            st.subheader('Resume wording suggestions — your approval required')
            st.write('These are editable starting points, not finished resume bullets.')
            approved = []
            for i, item in enumerate(analysis['suggestions']):
                st.markdown(f'**{i + 1}. {item["skill"]}**')
                st.caption('Original evidence: ' + item['source'])
                wording = st.text_area('Edit suggested wording', value=item['wording'], key=f'suggestion_{i}')
                if st.checkbox('Approve this wording', key=f'approve_{i}') and wording.strip():
                    approved.append(wording.strip())
            approved = list(dict.fromkeys(verified_drafts + approved))
            st.session_state.approved_suggestions = approved
            if approved:
                st.download_button('⬇️ Download approved wording', '\n\n'.join(approved), 'approved_resume_suggestions.txt', 'text/plain')
            st.info('Nothing is added to your resume automatically. You approve and download only the wording you want.')

elif page == 'Career Matches':
    st.title('🎯 Transferable Career Matches')
    st.write('Explore career paths outside newspaper publishing based on the responsibilities actually mentioned in your resume.')
    st.info('Free local matching combines resume phrase evidence with responsibilities you explicitly confirmed. Scores are not hiring predictions.')
    if not st.session_state.resume_text.strip():
        st.warning('First upload your resume on the My Resume page.')
    else:
        st.write('**Actual career background:** ' + (', '.join(st.session_state.confirmed_titles) or 'Group Newspaper Publisher'))
        st.caption('Your real title is not changed to match another industry.')
        st.write('**Confirmed responsibilities used in matching:**', len(st.session_state.verified_duties))
        st.caption('Edit these on Career Analysis → Experience Verification.')
        if st.button('Compare My Career Skills', type='primary'):
            st.session_state.career_matches = get_career_matches(st.session_state.resume_text)
        if 'career_matches' in st.session_state:
            results = st.session_state.career_matches
            industry_options = ['All industries'] + sorted({r['industry'] for r in results})
            industry = st.selectbox('Filter by industry', industry_options)
            visible = [r for r in results if industry == 'All industries' or r['industry'] == industry]
            st.caption('Overlap scores combine resume phrases and your confirmed responsibilities, weighted by career path. They are not hiring probabilities.')
            for r in visible:
                with st.expander(f"{r['title']} — {r['score']}% documented competency overlap", expanded=False):
                    st.write('**Industry:**', r['industry'])
                    st.progress(r['score'] / 100)
                    st.write('**Matched competency areas:**')
                    if r['matched']:
                        for skill in r['matched']:
                            st.markdown('**' + skill + '**')
                            if skill in r['evidence']:
                                st.caption('Resume phrase: ' + ' | '.join(r['evidence'][skill][:2]))
                            if skill in r['verified']:
                                st.caption('Confirmed by you: ' + '; '.join(d for d in st.session_state.verified_duties if VERIFICATION_AREAS[d] == skill))
                    else:
                        st.write('None from this starter competency list.')
                    st.write('**Responsibilities to confirm or document:**')
                    if r['unconfirmed']:
                        for skill in r['unconfirmed']:
                            st.write('• ' + skill)
                    else:
                        st.write('All mapped areas had phrase matches; verify that the duties were actually performed.')
                    st.write('**Resume tailoring idea:**', r['focus'])
                    st.caption('Only add achievements, responsibilities and numbers you can substantiate. Use Career Analysis to edit and approve suggested wording.')
            st.download_button('⬇️ Export Career Matches CSV',
                pd.DataFrame([{'Career':r['title'], 'Industry':r['industry'],
                    'Documented overlap (%)':r['score'],
                    'Matched areas':'; '.join(r['matched']),
                    'User-confirmed areas':'; '.join(r['verified']),
                    'Areas to verify':'; '.join(r['unconfirmed']),
                    'Resume focus':r['focus']} for r in visible]).to_csv(index=False),
                'career_matches.csv', 'text/csv')

elif page == 'Find Jobs':
    st.title('🔎 Find Real Jobs — Nationwide + Remote')
    st.write('Searches free public job feeds for remote opportunities accepting U.S. applicants. '
             'Nationwide on-site roles are not comprehensively covered by these sources.')
    st.caption('Sources: Jobicy, Himalayas and Remotive. Listings can expire and some sources update with a delay.')
    recommended = [r['title'] for r in get_career_matches(st.session_state.resume_text)] if st.session_state.resume_text.strip() else [r['title'] for r in CAREER_PATHS]
    with st.form('live_job_search'):
        role = st.selectbox('Career path', ['All recommended career paths'] + recommended)
        keywords = st.text_input('Optional keywords (try operations, leadership, business development)')
        arrangement = st.selectbox('Work arrangement', ['Nationwide + remote', 'Remote only'])
        max_results = st.slider('Maximum displayed jobs', 5, 60, 25, step=5)
        search = st.form_submit_button('Search Live Jobs', type='primary')
    if search:
        with st.spinner('Searching public job sources (may take up to a minute)...'):
            fetched, errors, counts = load_public_jobs()
        st.session_state.feed_diagnostics = (len(fetched), counts, errors)
        selected_roles = recommended if role == 'All recommended career paths' else [role]
        query = keywords.strip().lower()
        filtered = []
        for job in fetched:
            if not us_eligible(job):
                continue
            title = job['title'].lower()
            description = job['description'].lower()
            title_score = max((role_similarity(job['title'], r) for r in selected_roles), default=0)
            # Use transferable senior-management terms when the exact title differs.
            broad = bool(re.search(r'\b(operations|general manager|business development|partnerships|commercial|revenue|distribution|logistics|marketing|director|chief operating officer|publisher|regional manager)\b', title))
            extra = bool(query and query in (title + ' ' + description))
            if not (title_score or broad or extra):
                continue
            competency_hits = job_competency_hits(job, st.session_state.resume_text)
            rank = title_score * 4 + len(competency_hits) + (2 if extra else 0)
            filtered.append({**job, 'rank': rank, 'role_score': title_score, 'competency_hits': competency_hits})
        filtered.sort(key=lambda j: (-j['rank'], j['title'].lower()))
        st.session_state.search_results = filtered[:max_results]
        st.session_state.search_total = len(filtered)
        st.session_state.search_timestamp = str(date.today())
    if 'feed_diagnostics' in st.session_state:
        count, counts, errors = st.session_state.feed_diagnostics
        with st.expander('Search diagnostics — see what sources returned'):
            st.write(f'{count} unique postings fetched before career filtering.')
            st.write('Source counts:', counts)
            for error in errors:
                st.warning(error)
            st.caption('If a source is blocked or unavailable, its count may be missing. Results are cached for one hour.')
    if 'search_results' in st.session_state:
        results = st.session_state.search_results
        st.subheader(f'{len(results)} jobs displayed')
        st.caption(f'{st.session_state.get("search_total", len(results))} broad career-related postings • Searched {st.session_state.get("search_timestamp", "today")}. This is not a hiring-fit score.')
        if not results:
            st.info('No matches in the available free feeds. Check Search diagnostics for provider errors. '
                    'Try the keyword “operations” or a broader career path.')
        for i, job in enumerate(results):
            with st.container(border=True):
                st.markdown(f"**{job['title']}** — {job['company']}")
                st.write(f"📍 {job['location']} | Remote | {job['source']}")
                if job['salary']:
                    st.write('**Salary (as listed):**', job['salary'])
                st.caption('Potential experience overlap: ' + (', '.join(job['competency_hits']) if job['competency_hits'] else 'No explicit competency phrase matches'))
                st.caption('Check the full posting for U.S. eligibility, work authorization, location restrictions and qualifications.')
                if job['date']:
                    st.caption('Posted: ' + job['date'])
                st.link_button('View original posting / Apply', job['url'])
                if st.button('Save to Job Tracker', key=f'save_live_{i}'):
                    if any(j.get('Job URL') == job['url'] for j in st.session_state.jobs):
                        st.info('Already in your Job Tracker.')
                    else:
                        st.session_state.jobs.append({
                            'Company': job['company'], 'Job Title': job['title'],
                            'Location': job['location'], 'Job URL': job['url'],
                            'Salary': job['salary'], 'Status': 'Saved',
                            'Date Recorded': str(date.today()), 'Interview Date': '',
                            'Notes': f"Found via {job['source']}. Confirm eligibility and requirements before applying."
                        })
                        st.success('Saved to Job Tracker for this session.')
    st.warning('Job Tracker entries are not permanently stored yet. Export your CSV before ending your session.')

elif page == 'Job Tracker':
    st.title('📋 Job Application Tracker')
    with st.expander('➕ Add a New Job', expanded=True):
        with st.form('add_job'):
            company = st.text_input('Company')
            title = st.text_input('Job Title')
            location = st.text_input('Location')
            url = st.text_input('Job Posting URL')
            salary = st.text_input('Salary / Range')
            status = st.selectbox('Status', STATUSES)
            recorded = st.date_input('Date Recorded', value=date.today())
            interview = st.date_input('Interview Date (optional)', value=None)
            notes = st.text_area('Notes / Next Steps')
            if st.form_submit_button('Save Job'):
                if company.strip() and title.strip():
                    st.session_state.jobs.append({'Company':company.strip(),'Job Title':title.strip(),'Location':location.strip(),'Job URL':url.strip(),'Salary':salary.strip(),'Status':status,'Date Recorded':str(recorded),'Interview Date':str(interview) if interview else '', 'Notes':notes.strip()})
                    st.success('Job added.')
                else:
                    st.warning('Company and Job Title are required.')
    jobs = st.session_state.jobs
    if jobs:
        selected_status = st.selectbox('Filter by status', ['All'] + STATUSES)
        visible = [j for j in jobs if selected_status == 'All' or j['Status'] == selected_status]
        st.dataframe(pd.DataFrame(visible), use_container_width=True, hide_index=True)
        idx = st.selectbox('Update a job', range(len(jobs)), format_func=lambda i: f"{jobs[i]['Company']} — {jobs[i]['Job Title']}")
        job = jobs[idx]
        new_status = st.selectbox('New status', STATUSES, index=STATUSES.index(job['Status']))
        new_notes = st.text_area('Update notes', value=job['Notes'], key=f'notes_{idx}')
        if st.button('Save Changes'):
            jobs[idx]['Status'] = new_status
            jobs[idx]['Notes'] = new_notes
            st.success('Changes saved for this session.')
            st.rerun()
        st.download_button('⬇️ Export Job Tracker CSV', pd.DataFrame(jobs).to_csv(index=False), 'job_tracker.csv', 'text/csv')
    else:
        st.info('No jobs tracked yet.')
    st.warning('Tracker data is temporary. Export a CSV backup before closing your session. Permanent storage is a future step.')
