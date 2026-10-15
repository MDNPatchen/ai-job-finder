"""Pure job identity, preference filtering, and search-history helpers.

No network or UI side effects. These identities intentionally favor keeping
two different openings over accidentally hiding them.
"""
import hashlib
import re
from urllib.parse import urlsplit, parse_qsl, urlencode

TRACKING_KEYS = frozenset(('fbclid','gclid','mc_cid','mc_eid','ref',
                           'source','utm_source','utm_medium','utm_campaign',
                           'utm_term','utm_content'))
GENERIC_PATHS = frozenset(('', '/', '/jobs', '/job', '/careers',
                           '/search-jobs', '/job-search'))


def _normalize(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ',
                  str(value or '').casefold())).strip()


def canonical_job_url(value):
    """Strip analytics query parameters but preserve real requisition IDs."""
    try:
        url=urlsplit(str(value or '').strip())
        if url.scheme not in ('http','https') or not url.netloc:
            return ''
        query=[]
        for key,val in parse_qsl(url.query,keep_blank_values=True):
            if key.casefold() not in TRACKING_KEYS and not key.lower().startswith('utm_'):
                query.append((key,val))
        query.sort()
        path=url.path.rstrip('/') or '/'
        return (url.netloc.casefold().removeprefix('www.') +
                path + ('?'+urlencode(query) if query else ''))
    except (ValueError,TypeError):
        return ''


def distinct_posting_key(job):
    """Never merge distinct location/requisition URLs just for sharing a title.

    The same official URL dedupes, even if two feeds have different location
    text. A generic employer jobs directory is not a vacancy-specific URL;
    for those retain different locations but can't prove same-city duplicates.
    """
    employer=_normalize(job.get('company'))
    title=_normalize(job.get('title'))
    uri=canonical_job_url(job.get('url'))
    path='/' + uri.split('/',1)[1].split('?',1)[0].strip('/') if '/' in uri else '/'
    if uri and path.casefold() not in GENERIC_PATHS:
        return ('url',employer,title,uri)
    return ('location',employer,title,_normalize(job.get('location')),
            _normalize(job.get('date')))


def posting_id(job):
    key='\x1f'.join(distinct_posting_key(job))
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]


def annotate_new_results(jobs, previously_seen, has_baseline):
    """First search establishes a baseline rather than labeling all jobs new."""
    seen=set(previously_seen or ())
    result=[]
    for job in jobs:
        key=posting_id(job)
        result.append({**job, 'posting_id':key,
                       'new_since_last_search':bool(has_baseline and key not in seen)})
    return result, sorted(seen | {x['posting_id'] for x in result})


def salary_lower_bound(raw):
    """Return only an explicitly annual USD lower bound, never infer hourly."""
    value=str(raw or '').strip()
    if not value or re.search(r'\b(?:hourly|per hour|/hr|/hour|weekly|monthly|per week)\b',value,re.I):
        return None
    values=[]
    for amount,suffix in re.findall(r'\$\s*(\d[\d,]*(?:\.\d{1,2})?)\s*([kKmM]?)\b',value):
        try:
            val=float(amount.replace(',',''))
        except ValueError:
            continue
        if suffix.casefold()=='k':
            val*=1000
        elif suffix.casefold()=='m':
            val*=1000000
        if 20000<=val<=10000000:
            values.append(int(val))
    return min(values) if values else None


def seniority_label(title):
    title=str(title or '').casefold()
    if re.search(r'\b(publisher|group publisher)\b',title):
        return 'Publisher'
    if re.search(r'\b(chief|coo|ceo|cfo|president|vice president|vp|executive director|general manager)\b',title):
        return 'Executive / VP'
    if re.search(r'\b(director|head of|managing director)\b',title):
        return 'Director'
    if re.search(r'\b(manager|administrator|supervisor)\b',title):
        return 'Manager'
    return 'Other'


def preferences_allow(job, states, preferences):
    """A salary minimum applies only to verifiable annual amounts.

    Unknown compensation is kept unless the user specifically excludes it.
    An allowed-state restriction requires geographic evidence in the posting.
    """
    pref=preferences or {}
    known=set(states or [])
    if known & set(pref.get('excluded_states') or []):
        return False
    included=set(pref.get('included_states') or [])
    if included and not known.intersection(included):
        return False
    if pref.get('verified_workplace_only') and job.get('work_style')=='Not specified':
        return False
    allowed_roles=set(pref.get('seniority') or [])
    if allowed_roles and seniority_label(job.get('title')) not in allowed_roles:
        return False
    minimum=int(pref.get('minimum_salary') or 0)
    if minimum:
        lower=salary_lower_bound(job.get('salary'))
        if lower is None:
            return bool(pref.get('include_unlisted_salary',True))
        if lower<minimum:
            return False
    return True
