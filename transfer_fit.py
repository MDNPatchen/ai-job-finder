"""Transferable-strength scoring grounded in documented resume and job duties.

This is a comparative research score, not a probability of hiring or a formal
qualification determination. Employer title and industry are intentionally
weak signals. Missing evidence is a prompt to verify, not a disqualification.
"""
import re

# Broad capabilities supported by actual resume evidence or explicit user
# confirmations. No degree, seniority, industry or past job title is assumed.
# Modest weights reflect how reusable a skill tends to be across employers.
TRANSFER_WEIGHTS = {
    'Financial & P&L leadership': 1.25,
    'Multi-site business leadership': 1.20,
    'Operations leadership': 1.25,
    'Talent & organizational change': 1.20,
    'Revenue growth & transformation': 1.20,
    'Advertising & sales leadership': 1.05,
    'Editorial & cross-functional leadership': 1.05,
    'Digital transformation': 1.15,
    'Audience & marketing development': 1.10,
    'Distribution & logistics': 1.20,
    'Negotiation & vendor management': 1.20,
    'Strategic planning & execution': 1.20,
    'Community partnerships': 1.10,
    'Project & program management': 1.15,
    'Reporting & data analysis': 1.05,
    'Compliance & regulated operations': 1.05,
    'Healthcare administration': 1.00,
    'Government administration': 1.00,
}
TRANSFERABLE_AREAS = frozenset(TRANSFER_WEIGHTS)


def _weight(item):
    return TRANSFER_WEIGHTS.get(str(item.get('area') or ''), 1.0)


def _is_description_match(item):
    return item.get('match_origin') != 'Job title only'


def supported_transfer_areas(qualification):
    """Strengths tied to evidence in both the job duties and resume.

    Explicitly confirmed skills are recorded separately rather than silently
    treated as documented resume experience.
    """
    documented = [
        item for item in (qualification.get('resume_matches') or [])
        if _is_description_match(item)
    ]
    confirmed = [
        item for item in (qualification.get('confirmed_only') or [])
        if _is_description_match(item)
    ]
    documented.sort(key=lambda item:(-_weight(item),item['area']))
    confirmed.sort(key=lambda item:(-_weight(item),item['area']))
    return [{
        'area':item['area'],
        'evidence':'Documented in résumé',
        'job_excerpt':item.get('listing_excerpt') or '',
        'resume_excerpt':(item.get('resume_evidence') or [''])[0],
    } for item in documented] + [{
        'area':item['area'],
        'evidence':'Confirmed separately; add résumé evidence',
        'job_excerpt':item.get('listing_excerpt') or '',
        'resume_excerpt':'',
    } for item in confirmed]


def transfer_fit(qualification, job, title_alignment, specialty_penalty=0,
                 credential_penalty=0):
    """Rank the demonstrated overlap of job duties with reusable strengths.

    Job-title matches are discounted, uncorroborated confirmations get partial
    credit, and unfamiliar specialist requirements remain cautionary rather
    than automatic exclusion.
    """
    if not qualification.get('resume_present'):
        return {'index':0, 'duty_coverage':0,
                'transferable_strengths':[], 'description_matches':0}
    matched = qualification.get('resume_matches') or []
    confirmed = qualification.get('confirmed_only') or []
    missing = qualification.get('not_documented') or []
    all_areas = matched + confirmed + missing
    possible = max(6.0, sum(_weight(item) for item in all_areas))
    supported = sum(
        _weight(item) * (1.0 if _is_description_match(item) else 0.30)
        for item in matched)
    supported += sum(
        _weight(item) * (0.45 if _is_description_match(item) else 0.12)
        for item in confirmed)
    coverage = min(100, round(100 * supported / possible))
    description_matches = sum(_is_description_match(x) for x in matched)
    # Evidence breadth only counts job-description duties corroborated by the
    # resume. A grand title without actual duties cannot earn this bonus.
    breadth = min(8, max(0, description_matches - 1) * 2)
    # A title contributes at most ~8 points, vs up to 82 for documented fit.
    title_contribution = 0.08 * max(0, min(100, title_alignment))
    raw = round(0.82 * coverage + title_contribution + breadth -
                specialty_penalty - credential_penalty)
    # Very sparse postings cannot substantiate a near-perfect match.
    if len(re.sub(r'\s+', ' ', str(job.get('description') or '')).strip()) < 250:
        raw = min(raw, 74)
    return {
        'index': max(0, min(96, raw)),
        'duty_coverage': coverage,
        'transferable_strengths': supported_transfer_areas(qualification),
        'description_matches': description_matches,
    }
