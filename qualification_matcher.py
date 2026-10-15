"""Explain job/resume overlap using supplied text, with no AI or paid API.

An absent resume phrase never proves the applicant lacks a qualification.
Required credentials and years are flagged for human verification.
"""
import re
from functools import lru_cache
from qualification_v2 import extract_requirements, recalibrate_match

CAPABILITIES = (
    ('Financial & P&L leadership', (r'\bp\s*&\s*l\b', r'profit and loss', r'profitability', r'\bbudgets?\b', r'\bbudgeting\b', r'financial (?:management|planning|performance|oversight)', r'\bforecast(?:ing|s)?\b', r'cash flow')),
    ('Multi-site business leadership', (r'multi[- ](?:site|location|unit)', r'multiple (?:sites|locations|facilities|publications|branches|businesses)', r'regional (?:leadership|management|operations)', r'\bgroup publisher\b', r'\bdistrict (?:director|manager)\b')),
    ('Operations leadership', (r'\boperations? (?:management|leadership|director|manager|oversight|strategy|improvement)\b', r'operational (?:excellence|efficien\w*|performance|management|leadership)', r'process improvement', r'\bworkflow\b', r'\bcontinuous improvement\b', r'\boperational planning\b')),
    ('Talent & organizational change', (r'\b(?:supervis\w*|manag\w*|lead\w*) (?:staff|employees|teams|managers|people|personnel)\b', r'\b(?:hiring|recruitment|onboarding|training|mentoring|coaching)\b', r'\borganizational (?:change|development|transformation)\b', r'\bchange management\b', r'\bworkforce\b', r'\bemployee relations\b')),
    ('Revenue growth & transformation', (r'\brevenue\b', r'\bsales (?:growth|strategy|management|leadership|teams?)\b', r'\bbusiness development\b', r'\bcommercial strategy\b', r'\bturnaround\b', r'\bmarket (?:growth|expansion)\b')),
    ('Advertising & sales leadership', (r'\badvertis\w*\b', r'\b(?:sales|account) (?:team|leadership|executives?|management|strategy)\b', r'\bclient acquisition\b', r'\baccounts? management\b')),
    ('Editorial & cross-functional leadership', (r'\beditorial\b', r'\bnewsroom\b', r'\bmanaging editor\b', r'\bpublisher\b', r'\bcross[- ]functional (?:teams?|leadership|management)\b')),
    ('Digital transformation', (r'\bdigital (?:revenue|marketing|strategy|transformation|products?|subscriptions?|platforms?)\b', r'\bonline advertising\b', r'\btechnology adoption\b', r'\be-?commerce\b')),
    ('Audience & marketing development', (r'\bmarketing\b', r'\baudience (?:growth|development|engagement)\b', r'\bcustomer (?:acquisition|retention|growth)\b', r'\bcirculation\b', r'\bsubscription\w*\b', r'\bbrand strategy\b')),
    ('Distribution & logistics', (r'\bdistribution\b', r'\blogistics\b', r'\bsupply chain\b', r'\bdelivery (?:network|operations|routes?)\b', r'\broute (?:optimization|planning|management)\b', r'\binventory management\b', r'\bfulfillment\b')),
    ('Negotiation & vendor management', (r'\bnegotiat\w*\b', r'\b(?:vendor|supplier|contract|procurement|purchasing) (?:management|negotiation|oversight|administration|relations)\b', r'\b(?:vendor|supplier|contract)\b')),
    ('Strategic planning & execution', (r'\bstrategic (?:planning|initiatives|priorities|direction)\b', r'\bstrategy (?:development|execution|implementation)\b', r'\bbusiness plans?\b', r'\bperformance (?:goals|metrics|improvement)\b')),
    ('Community partnerships', (r'\bcommunity (?:relations|engagement|partnerships|outreach)\b', r'\bstakeholder\w*\b', r'\bstrategic partnerships?\b', r'\bexternal relations\b', r'\bpublic affairs\b')),
    ('Project & program management', (r'\bproject (?:management|manager|delivery|planning|execution)\b', r'\bprogram (?:management|manager|administration|delivery)\b', r'\bportfolio management\b')),
    ('Reporting & data analysis', (r'\b(?:data|financial|business) analys\w*\b', r'\b(?:kpi|kpis|dashboards?|analytics|reporting|metrics)\b', r'\bperformance measurement\b')),
    ('Compliance & regulated operations', (r'\b(?:regulatory|legal|policy|industry) compliance\b', r'\brisk management\b', r'\bregulat\w*\b', r'\baudit\w*\b')),
    ('Healthcare administration', (r'\b(?:healthcare|clinical|hospital|patient|medical) (?:administration|operations|management|services|experience)\b', r'\bhealth system\b', r'\bpatient care\b')),
    ('Government administration', (r'\b(?:city|county|municipal|public sector|government) (?:administration|management|operations|leadership)\b', r'\bpublic administration\b', r'\bmunicipal services\b')),
)
_COMPILED = tuple((area, tuple(re.compile(term, re.I) for term in patterns))
                  for area, patterns in CAPABILITIES)


def _one_line(text, limit=260):
    return re.sub(r'\s+', ' ', str(text or '')).strip()[:limit]


def _excerpt(text, found, radius=95):
    left = max(0, found.start() - radius)
    right = min(len(text), found.end() + radius)
    if left > 0:
        boundary = text.find(' ', left, min(left + 25, len(text)))
        if boundary >= 0:
            left = boundary + 1
    if right < len(text):
        boundary = text.rfind(' ', max(0, right - 25), right)
        if boundary > left:
            right = boundary
    excerpt = _one_line(text[left:right], 225)
    return ('…' if left > 0 else '') + excerpt + ('…' if right < len(text) else '')


@lru_cache(maxsize=8)
def compile_resume_profile(resume_text, confirmed_areas=()):
    """Use literal resume excerpts and keep user confirmations separate."""
    text = str(resume_text or '')[:55000]
    lines = [_one_line(line, 500) for line in text.splitlines() if line.strip()]
    evidence = {}
    for area, patterns in _COMPILED:
        matches = []
        for line in lines:
            if any(p.search(line) for p in patterns):
                if line not in matches:
                    matches.append(line[:280])
            if len(matches) == 2:
                break
        if matches:
            evidence[area] = matches
    return {'resume_present': bool(text.strip()), 'evidence': evidence,
            'confirmed': frozenset(confirmed_areas)}


def _qualification_screeners(description, resume):
    """Check only requirements visible in the supplied job text."""
    return extract_requirements(description, resume)


def assess_job_qualifications(job, profile, resume_text=''):
    """Grounded overlap assessment, not a credential or hiring-eligibility verdict."""
    description = str(job.get('description') or '')[:16000]
    job_title = str(job.get('title') or '')
    matched, confirmed_only, missing = [], [], []
    for area, patterns in _COMPILED:
        found = next((m for pattern in patterns if (m := pattern.search(description))), None)
        origin = 'Job description'
        source = description
        if found is None:
            found = next((m for pattern in patterns if (m := pattern.search(job_title))), None)
            origin = 'Job title only'
            source = job_title
        if found is None:
            continue
        entry = {'area': area, 'listing_excerpt': _excerpt(source, found),
                 'match_origin': origin}
        if area in profile['evidence']:
            matched.append({**entry, 'resume_evidence': profile['evidence'][area]})
        elif area in profile['confirmed']:
            confirmed_only.append(entry)
        else:
            missing.append(entry)
    screeners = _qualification_screeners(description, resume_text)
    m, c, n = len(matched), len(confirmed_only), len(missing)
    if not profile['resume_present']:
        label = 'Upload a resume for evidence-based matching'
    elif m >= 3 and m / max(1, m+c+n) >= .58:
        label = 'Strong resume overlap — check requirements'
    elif m >= 1:
        label = 'Some relevant resume evidence'
    elif c:
        label = 'Experience confirmed separately; add resume evidence'
    else:
        label = 'Limited overlap visible in resume'
    if m:
        focus = ('Tailor your resume using real examples of ' +
                 ', '.join(x['area'].lower() for x in matched[:2]) +
                 '. Add outcomes or numbers only if you can substantiate them.')
    elif c:
        focus = ('Consider adding factual examples for your separately confirmed ' +
                 confirmed_only[0]['area'].lower() + ' experience.')
    else:
        focus = 'Review the listed duties and minimum requirements before applying; no experience has been assumed.'
    rank_bonus = min(6, 2*m + c)
    if profile['resume_present']:
        rank_bonus -= min(2, sum(1 for x in screeners
                                 if x['type'] == 'License / certification'
                                 and x['resume_status'] == 'Not verified from resume'))
    result = {'label': label, 'resume_matches': matched,
              'confirmed_only': confirmed_only,
              'not_documented': missing, 'screeners': screeners,
              'total_areas': m+c+n, 'rank_bonus': rank_bonus,
              'resume_focus': focus, 'resume_present': profile['resume_present']}
    review = recalibrate_match(job, result, resume_text)
    result['fit_index'] = review['index']
    result['role_alignment_index'] = review['role_alignment']
    result['specialized_requirements'] = review['specialties']
    result['cautions'] = review['cautions']
    result['description_completeness'] = review['confidence']
    result['transferable_strengths'] = review['transferable_strengths']
    result['duty_coverage_index'] = review['duty_coverage']
    if review['cautions'] and label.startswith('Strong resume overlap'):
        result['label'] = 'Strong transferable overlap — important requirements to verify'
    return result
