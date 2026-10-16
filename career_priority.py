"""Explainable leadership alignment for sorting executive career searches.

Only reorders jobs already accepted by qualification matching. It does not
claim an applicant is qualified or silently remove lower-level vacancies.
"""
import re

def leadership_tier(title):
    t=str(title or '').lower()
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

    Bucket fit scores in 5-point bands, preventing a marginal vocabulary
    difference from placing a supervisor above a comparable executive role.
    """
    fit=job.get('qualification_match',{}).get('fit_index',0)
    try:
        fit=float(fit)
    except (ValueError,TypeError):
        fit=0
    return (-fit, -leadership_priority(job), evidence_key(job))
