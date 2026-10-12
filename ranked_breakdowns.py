"""Deterministic resume-evidence ordering and downloadable job qualification breakdowns.

The evidence index is NOT a hiring probability, required-qualification score,
verified eligibility claim, or judgment about the applicant.

Only the uploaded resume's cited evidence and separately confirmed experience
contribute. The conservative five-area baseline prevents a one-sentence
description mentioning one common skill from scoring 100/100.
"""

import re


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


def breakdowns_json(jobs):
    """Structured ranked information, with no uncited entire-resume export."""
    out = []
    for place, job in enumerate(jobs, 1):
        q = job.get('qualification_match') or {}
        out.append({
            'rank': place,
            'job_title': job.get('title') or '',
            'employer': job.get('company') or '',
            'location': job.get('location') or '',
            'work_arrangement': job.get('work_style') or 'Not specified',
            'posted_date': job.get('date') or '',
            'job_url': job.get('url') or '',
            'source': job.get('source') or '',
            'evidence_match_index': evidence_index(q),
            'role_alignment_index': q.get('role_alignment_index'),
            'specialized_experience_to_verify': q.get('specialized_requirements') or [],
            'important_cautions': q.get('cautions') or [],
            'description_completeness': q.get('description_completeness') or 'Not assessed',
            'index_explanation': ('Comparative fit index, 0–96: resume evidence plus role '
                                  'alignment, with caution for specialized requirements '
                                  'and credentials not verified from the resume. '
                                  'Not an eligibility score or hiring probability.'),
            'alignment_label': q.get('label') or 'Not assessed',
            'total_relevant_areas_detected': int(q.get('total_areas') or 0),
            'documented_resume_matches': q.get('resume_matches') or [],
            'user_confirmed_only': q.get('confirmed_only') or [],
            'not_documented_in_resume': q.get('not_documented') or [],
            'formal_requirements_to_verify': q.get('screeners') or [],
            'resume_tailoring_focus': q.get('resume_focus') or ''
        })
    return out


def breakdowns_csv_rows(jobs):
    """Flat rows for Excel; detailed posting excerpts stay available in JSON."""
    rows = []
    for item in breakdowns_json(jobs):
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
            'Evidence overlap index (0-100, not hiring probability)': item['evidence_match_index'],
            'Alignment': item['alignment_label'],
            'Role-family alignment index': item['role_alignment_index'],
            'Specialized experience to verify': '; '.join(
                x.get('area') or '' for x in item['specialized_experience_to_verify']
                if x.get('needs_verification')),
            'Important qualification cautions': ' | '.join(item['important_cautions']),
            'Job-description completeness': item['description_completeness'],
            'Employer': item['employer'],
            'Job title': item['job_title'],
            'Location': item['location'],
            'Work arrangement': item['work_arrangement'],
            'Date posted': item['posted_date'],
            'Job URL': item['job_url'],
            'Source': item['source'],
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
