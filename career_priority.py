"""Explainable leadership alignment for sorting executive career searches.

Only reorders jobs already accepted by qualification matching. It does not
claim an applicant is qualified or silently remove lower-level vacancies.
"""
import re
import math

def leadership_tier(title):
    t=str(title or '').lower()
    # A senior person's title in a support role is not the applicant's level.
    if re.search(r'\bexecutive assistant\b|\b(?:assistant|coordinator|support)\s+to\b|'
                 r"\b(?:president|ceo|coo|director)(?:[’']s)?\s+assistant\b",t):
        return 0
    if re.search(r'\b(?:assistant|associate)\s+(?:general|regional|district|area)\s+manager\b',t):
        return 1
    if re.search(r'\b(?:assistant|associate|deputy)\s+(?:manager|director)\b', t):
        return 2
    if re.search(r'\b(?:group publisher|publisher|chief operating officer|chief executive officer|coo|ceo|president|vice president|\bvp\b|executive director|general manager|county manager|city manager)\b',t):
        return 4
    if re.search(r'\b(?:regional|district|area|group|multi[- ]site|multi[- ]unit)\s+(?:operations?\s+)?(?:director|manager|administrator)\b',t):
        return 4
    if re.search(r'\b(?:director|head of|administrator)\b',t):
        return 3
    if re.search(r'\b(?:supervisor|coordinator|assistant|associate|specialist|analyst)\b',t):
        return 0
    if re.search(r'\bmanager\b',t):
        return 1
    return 2

def leadership_priority(job):
    """Tie-break evidence-driven search results, not replace evidence score."""
    return leadership_tier(job.get('title'))

def career_sort_key(job, evidence_key):
    """Fit evidence remains first; title tier resolves nearby fit differences.

    Strict fit order is retained for compatibility; leadership review is an
    explicit separate order with transparent adjustments.
    """
    fit=job.get('qualification_match',{}).get('fit_index',0)
    try:
        fit=float(fit)
    except (ValueError,TypeError):
        fit=0
    return (-fit, -leadership_priority(job), evidence_key(job))


def career_review_category(title):
    """Partition every title into exactly one review category."""
    tier = leadership_tier(title)
    if tier >= 3:
        return 'Director / executive / publisher'
    if tier in (1, 2):
        return 'Management / related roles'
    return 'Other roles'


def has_detailed_description(job):
    """Require usable duties as well as known provenance."""
    from description_quality import assess_description
    return assess_description(job)['detailed']


def review_priority_details(job):
    """Auditable review adjustments; never modify the comparative fit index."""
    from description_quality import assess_description
    q=job.get('qualification_match') or {}
    try:
        fit=float(q.get('fit_index') or 0)
    except (ValueError,TypeError):
        fit=0
    if not math.isfinite(fit):
        fit=0
    fit=max(0,min(96,fit))
    role_caution={4:0,3:0,2:8,1:12,0:18}[leadership_tier(job.get('title'))]
    evidence_caution=0 if assess_description(job)['detailed'] else 15
    return {'priority':round(fit-role_caution-evidence_caution,2),
            'role_adjustment':role_caution,'description_adjustment':evidence_caution}


def leadership_review_priority(job):
    return review_priority_details(job)['priority']


def order_for_review(jobs, mode):
    """Do not mutate cached results; downloads and cards use this same order."""
    from ranked_breakdowns import evidence_sort_key
    copied=[dict(job,review_order=mode) for job in jobs]
    if mode=='Leadership priorities':
        return sorted(copied,key=lambda j:(-leadership_review_priority(j),
                      -leadership_tier(j.get('title')),evidence_sort_key(j)))
    return sorted(copied,key=evidence_sort_key)
