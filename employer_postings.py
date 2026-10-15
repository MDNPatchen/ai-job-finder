"""Conservative source screening for employer-direct job results.

An employer-named ATS feed and a unique vacancy URL are evidence of where a
listing originated; neither establishes that the vacancy remains open or that
the hiring company has been independently authenticated.
"""
import re
from urllib.parse import urlsplit, parse_qsl

DIRECT_EMPLOYER_SOURCES = frozenset({
    'NEOGOV', 'NEOED Schooljobs', 'NYC Open Data', 'Greenhouse',
    'Ashby', 'SmartRecruiters', 'Lever employer', 'Workable employer',
    'Mayo Clinic', 'USAJOBS',
})

KNOWN_RECRUITERS = frozenset({
    'keller executive search', 'hoa talent', 'jobot', 'cybercoders',
    'michael page', 'robert half', 'randstad', 'adecco', 'hays',
    'manpower', 'aerotek', 'actalent', 'teksystems', 'insight global',
    'kforce', 'vaco', 'motion recruitment', 'beacon hill staffing',
    'talentburst', 'lucas group', 'blue signal search', 'lhh',
})
RECRUITER_NAME_PATTERN = re.compile(
    r'\b(?:executive search|staffing|recruit(?:er|ers|ing|ment)|'
    r'employment agency|placement agency|headhunt(?:er|ers|ing)|'
    r'search partners|talent acquisition partners)\b', re.I)

# A generic career search page does not link to the particular vacancy.
DIRECTORY_PATHS = frozenset({
    '/', '/job', '/jobs', '/career', '/careers', '/employment',
    '/opportunities', '/positions', '/open-positions',
    '/job-search', '/search-jobs', '/jobs/search', '/jobs/get-started.page',
    '/careers/jobs', '/careers/search',
})
REQUISITION_KEYS = frozenset({
    'jobid', 'job_id', 'job', 'gh_jid', 'postingid', 'posting_id',
    'requisitionid', 'requisition_id', 'reqid', 'jid',
})


def is_recruiter_employer(company):
    """Recognize clearly named intermediaries, not mere recruiting language in a job ad."""
    name = re.sub(r'\s+', ' ', str(company or '').strip()).casefold()
    return name in KNOWN_RECRUITERS or bool(RECRUITER_NAME_PATTERN.search(name))


def is_individual_vacancy_url(url):
    """Require HTTPS and a job-specific route/ID, not a generic job directory.

    This is URL-structure screening, not a live vacancy or employer verification.
    """
    try:
        u = urlsplit(str(url or '').strip())
        if u.scheme != 'https' or not u.hostname:
            return False
        path = re.sub(r'/+', '/', u.path).rstrip('/').casefold() or '/'
        keys = {key.casefold() for key, val in parse_qsl(u.query) if val}
        if keys.intersection(REQUISITION_KEYS):
            return True
        if path in DIRECTORY_PATHS:
            return False
        if path.endswith('/get-started.page'):
            return False
        host = u.hostname.casefold()
        segments = [part for part in path.split('/') if part]
        if host in {'cityjobs.nyc.gov', 'www1.nyc.gov', 'nyc.gov'}:
            return bool(len(segments) > 1 and segments[0] in ('job', 'jobs')
                        and segments[-1] not in ('search', 'apply', 'get-started.page'))
        if host.endswith('smartrecruiters.com'):
            return len(segments) >= 2
        if host.endswith('lever.co') or host.endswith('ashbyhq.com'):
            return len(segments) >= 2
        if host.endswith('greenhouse.io'):
            return len(segments) >= 3 and ('jobs' in segments or 'job' in segments)
        if host.endswith('governmentjobs.com'):
            return 'jobs' in segments and segments.index('jobs') < len(segments)-1
        if host.endswith('workable.com'):
            return len(segments) >= 2 and ('j' in segments or 'jobs' in segments)
        if host.endswith('usajobs.gov'):
            return bool(re.search(r'/(?:getjob|job)/\d+', path))
        return bool(segments and segments[-1] not in (
            'search', 'job-search', 'jobs', 'career', 'careers', 'openings',
            'opportunities', 'all-jobs', 'all-positions'))
    except (ValueError, TypeError):
        return False


def is_foreign_location(location):
    """Exclude explicitly foreign locations, including province + CA ambiguities."""
    text = str(location or '').strip()
    if re.search(r'\b(?:Canada|United Kingdom|Australia|India|Germany|France|'
                 r'Ireland|Netherlands|Philippines|Pakistan)\b', text, re.I):
        return True
    # 'Toronto, ON, CA' must not pass as a California opening.
    return bool(re.search(
        r',\s*(?:AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\s*,\s*CA\s*$',
        text, re.I))


def posting_quality(job):
    """Explain why a listing passes or needs further verification."""
    return {
        'recruiter': is_recruiter_employer(job.get('company')) or
                     str(job.get('employer_identity_kind') or '').startswith('Recruiting intermediary'),
        'direct_source': str(job.get('source') or '') in DIRECT_EMPLOYER_SOURCES,
        'individual_url': is_individual_vacancy_url(job.get('url')),
        'foreign_location': is_foreign_location(job.get('location')),
    }
