"""Deterministic resume-evidence ordering and downloadable job qualification breakdowns.

The evidence index is NOT a hiring probability, required-qualification score,
verified eligibility claim, or judgment about the applicant.

Only the uploaded resume's cited evidence and separately confirmed experience
contribute. The conservative five-area baseline prevents a one-sentence
description mentioning one common skill from scoring 100/100.
"""

import re
from career_priority import leadership_tier


def _safe_spreadsheet_value(value):
    """Keep untrusted job/resume excerpts from being Excel formula cells."""
    if isinstance(value, str) and re.match(r'^[\s\ufeff]*[=+@-]', value):
        return "'" + value
    return value


def evidence_index(qualification):
    """0–100 index measuring explained resume overlap, NOT job eligibility."""
    if not qualification or not qualification.get('resume_present'):
        return 0
    if isinstance(qualification.get('fit_index'), (int, float)):
        return max(0, min(96, round(qualification['fit_index'])))
    documented = len(qualification.get('resume_matches') or [])
    confirmed = len(qualification.get('confirmed_only') or [])
    total = max(5, int(qualification.get('total_areas') or 0))
    # User-confirmed experience without written resume evidence has half weight;
    # requirements omitted from the source posting cannot be verified.
    return min(100, round(100 * (documented + 0.5 * confirmed) / total))


def evidence_sort_key(job):
    """Best documented qualification match first; existing title rank breaks ties."""
    q = job.get('qualification_match') or {}
    documented = len(q.get('resume_matches') or [])
    confirmed = len(q.get('confirmed_only') or [])
    day = (job.get('date') or '').replace('-', '')
    posted = int(day) if day.isdigit() else 0
    return (-evidence_index(q), -documented, -confirmed,
            -int(job.get('rank') or 0), -posted,
            str(job.get('title') or '').casefold(),
            str(job.get('company') or '').casefold())


def breakdowns_json(jobs, matching_version='', search_run_id=''):
    """Structured ranked information, with no uncited entire-resume export."""
    out = []
    for place, job in enumerate(jobs, 1):
        q = job.get('qualification_match') or {}
        out.append({
            'rank': place,
            'matching_engine_version': matching_version or 'not recorded',
            'search_run_id': search_run_id or 'not recorded',
            'job_title': job.get('title') or '',
            'career_level': ('Executive / multi-site leadership' if leadership_tier(job.get('title'))==4
                             else 'Director leadership' if leadership_tier(job.get('title'))==3
                             else 'Related leadership / other' if leadership_tier(job.get('title'))==2
                             else 'Manager' if leadership_tier(job.get('title'))==1
                             else 'Supervisor / specialist'),
            'employer': job.get('company') or '',
            'employer_identity_kind': job.get('employer_identity_kind') or
                                      'Company named by source; identity not independently verified',
            'work_arrangement_conflict': job.get('workplace_conflict') or '',
            'work_arrangement_source': job.get('arrangement_source') or
                                       'No explicit workplace label in public posting',
            'location': job.get('location') or '',
            'work_arrangement': job.get('work_style') or 'Not specified',
            'posted_date': job.get('date') or '',
            'job_url': job.get('url') or '',
            'source': job.get('source') or '',
            'job_description_source': job.get('description_source') or 'Source detail depth unknown',
            'evidence_match_index': evidence_index(q),  # legacy JSON key
            'comparative_fit_index': evidence_index(q),
            'role_alignment_index': q.get('role_alignment_index'),
            'job_duty_coverage_index': q.get('duty_coverage_index'),
            'transferable_strengths': q.get('transferable_strengths') or [],
            'specialized_experience_to_verify': q.get('specialized_requirements') or [],
            'career_fit_cautions': q.get('career_fit_cautions') or [],
            'career_fit_ranking_caution': q.get('career_fit_penalty') or 0,
            'posting_requirement_checks': q.get('posting_requirement_checks') or [],
            'posting_requirement_caution': q.get('posting_requirement_penalty') or 0,
            'overlapping_specialist_deductions_avoided': q.get('ranking_overlap_relief') or 0,
            'ranking_caution_calibration': q.get('ranking_overlap_note') or '',
            'internal_only_restriction': bool(q.get('application_restricted')),
            'important_cautions': q.get('cautions') or [],
            'description_completeness': q.get('description_completeness') or 'Not assessed',
            'index_explanation': ('Transferable-strength fit index, 0–96: primarily '
                                  'documented résumé strengths shared with listed duties, '
                                  'with minor title influence and caution for specialized '
                                  'requirements or credentials not verified. '
                                  'Overlapping field-experience cautions are counted only once '
                                  'across title, domain and stated requirements; '
                                  'required degrees and application rules stay separate. '
                                  'Preferred criteria do not '
                                  'count as required. Not an eligibility score '
                                  'or hiring probability.'),
            'alignment_label': q.get('label') or 'Not assessed',
            'total_relevant_areas_detected': int(q.get('total_areas') or 0),
            'documented_resume_matches': q.get('resume_matches') or [],
            'user_confirmed_only': q.get('confirmed_only') or [],
            'not_documented_in_resume': q.get('not_documented') or [],
            'formal_requirements_to_verify': q.get('screeners') or [],
            'resume_tailoring_focus': q.get('resume_focus') or ''
        })
    return out


def breakdowns_csv_rows(jobs, matching_version='', search_run_id=''):
    """Flat rows for Excel; detailed posting excerpts stay available in JSON."""
    rows = []
    for item in breakdowns_json(jobs, matching_version, search_run_id):
        def areas(value):
            return '; '.join(x.get('area') or '' for x in value)
        def quotes(value):
            return ' | '.join(
                str(v.get('area') or '') + ': ' + str(snippet)
                for v in value
                for snippet in (v.get('resume_evidence') or [])[:2])
        def requirements(value):
            return ' | '.join(
                str(x.get('type') or '') + ': ' + str(x.get('priority') or '') +
                ' — ' + str(x.get('listing_excerpt') or '')
                for x in value)
        rows.append({
            'Rank': item['rank'],
            'Matching engine version': item['matching_engine_version'],
            'Search run ID (UTC)': item['search_run_id'],
            'Comparative fit index (0-96; not hiring probability)': item['comparative_fit_index'],
            'Alignment': item['alignment_label'],
            'Role-family alignment index': item['role_alignment_index'],
            'Job-duty overlap index': item['job_duty_coverage_index'],
            'Top transferable strengths documented in resume': '; '.join(
                x['area'] for x in item['transferable_strengths']
                if x.get('evidence') == 'Documented in résumé'),
            'Transferable strengths confirmed separately': '; '.join(
                x['area'] for x in item['transferable_strengths']
                if x.get('evidence') != 'Documented in résumé'),
            'Additional career-fit cautions': '; '.join(
                str(x.get('area') or '') + ': ' + str(x.get('reason') or '')
                for x in item['career_fit_cautions']),
            'Career-fit ranking caution (points)': item['career_fit_ranking_caution'],
            'Overlapping specialist deductions avoided (points)': item['overlapping_specialist_deductions_avoided'],
            'Ranking caution calibration': item['ranking_caution_calibration'],
            'Specialized experience to verify': '; '.join(
                (x.get('area') or '') + ' [' + (x.get('priority') or 'verify') + ']'
                for x in item['specialized_experience_to_verify']
                if x.get('needs_verification')),
            'Important qualification cautions': ' | '.join(item['important_cautions']),
            'Job-description completeness': item['description_completeness'],
            'Career level (title-based)': item['career_level'],
            'Employer': item['employer'],
            'Employer identification': item['employer_identity_kind'],
            'Work arrangement evidence': item['work_arrangement_source'],
            'Workplace labeling conflict': item['work_arrangement_conflict'],
            'Posting explicitly restricts to internal applicants': (
                'Yes — verify eligibility' if item['internal_only_restriction'] else 'No explicit restriction detected'),
            'Employer minimum requirements to verify': ' | '.join(
                x['area'] + ' [' + x['priority'] + '] ' +
                x['listing_excerpt']
                for x in item['posting_requirement_checks']),
            'Employer-specific ranking cautions (points)': item['posting_requirement_caution'],
            'Job title': item['job_title'],
            'Location': item['location'],
            'Work arrangement': item['work_arrangement'],
            'Date posted': item['posted_date'],
            'Job URL': item['job_url'],
            'Source': item['source'],
            'Job description completeness source': item['job_description_source'],
            'Documented match count': len(item['documented_resume_matches']),
            'Total relevant areas in posting': item['total_relevant_areas_detected'],
            'Resume-supported qualifications': areas(item['documented_resume_matches']),
            'Actual resume excerpts': quotes(item['documented_resume_matches']),
            'User-confirmed but not documented': areas(item['user_confirmed_only']),
            'Areas needing verification': areas(item['not_documented_in_resume']),
            'Education, license and experience checks': requirements(
                item['formal_requirements_to_verify']),
            'Resume tailoring focus': item['resume_tailoring_focus']
        })
    return [{key:_safe_spreadsheet_value(value) for key,value in row.items()}
            for row in rows]
