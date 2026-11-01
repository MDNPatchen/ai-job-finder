"""Public Workday job boards (the *.myworkdayjobs.com "CXS" API).

Large employers post thousands of openings, so a board is not paged in
full: it is searched for leadership terms, titles are screened first, and
full details (description, posting date, country, workplace type) are fetched
only for titles that could match. Partial coverage is reported, never hidden.
"""
import json
import re
from urllib.parse import quote

from source_http import request_budget
from source_result import SourceRecords

SEARCH_TERMS = ('director', 'manager', 'executive', 'vice president')
PAGE_SIZE = 20          # Workday's public API caps a page at 20
PAGES_PER_TERM = 2
MAX_DETAILS = 25
_US = re.compile(r'\b(?:united states|usa|u\.s\.a?\.?)\b', re.I)


def board_root(tenant, wd, site):
    return f'https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}'


def public_url(tenant, wd, site, external_path):
    return f'https://{tenant}.{wd}.myworkdayjobs.com/en-US/{site}{external_path}'


def _arrangement(info):
    text = ' '.join(str(info.get(k) or '') for k in ('remoteType', 'workplaceType', 'timeType'))
    for label in ('Hybrid', 'Remote', 'On-site', 'Onsite', 'On Site'):
        if label.lower() in text.lower():
            return 'On-site' if label.lower().startswith('on') else label
    return ''


def fetch_board(board, post_json, get_json, normalize, classify, parse_date, max_age,
                today, terms=SEARCH_TERMS, pages_per_term=PAGES_PER_TERM, max_details=MAX_DETAILS):
    """board = (token "tenant|wd|site", employer name). Returns SourceRecords."""
    token, employer = board[0], board[1]
    tenant, wd, site = token.split('|')
    root = board_root(tenant, wd, site)
    seen, candidates = set(), []
    listed = 0
    issue = ''
    truncated = False
    with request_budget(60):
        for term in terms:
            for page in range(pages_per_term):
                body = {'appliedFacets': {}, 'limit': PAGE_SIZE, 'offset': page * PAGE_SIZE, 'searchText': term}
                try:
                    data = post_json(root + '/jobs', body)
                    rows = data.get('jobPostings')
                    if not isinstance(rows, list):
                        raise ValueError('Workday response has no jobPostings')
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    if not listed and term == terms[0] and page == 0:
                        raise
                    issue = type(exc).__name__
                    break
                listed += len(rows)
                for row in rows:
                    path = row.get('externalPath') if isinstance(row, dict) else None
                    if not path or path in seen:
                        continue
                    seen.add(path)
                    if classify(row.get('title')):
                        candidates.append(row)
                total = int(data.get('total') or 0)
                if (page + 1) * PAGE_SIZE >= total:
                    break
                if page == pages_per_term - 1:
                    truncated = True
        if len(candidates) > max_details:
            truncated = True
        jobs, failed = [], 0
        for row in candidates[:max_details]:
            try:
                detail = get_json(root + row['externalPath'])
                info = detail.get('jobPostingInfo') or {}
            except (OSError, ValueError, TypeError, KeyError):
                failed += 1
                continue
            country = str((info.get('country') or {}).get('descriptor') or '')
            if country and not _US.search(country):
                continue
            posted = parse_date(info.get('startDate') or info.get('postedOn'))
            if not posted or (today - posted).days > max_age or posted > today:
                continue
            location = info.get('location') or row.get('locationsText') or ''
            extra = [x for x in (info.get('additionalLocations') or []) if isinstance(x, str)]
            if extra:
                location = '; '.join([location, *extra[:3]])
            url = info.get('externalUrl') or public_url(tenant, wd, site, row['externalPath'])
            hiring = (detail.get('hiringOrganization') or {}).get('name') or employer
            job = normalize(info.get('title') or row.get('title'), hiring if hiring else employer, url,
                            location, info.get('jobDescription') or '', 'Workday', False, '',
                            info.get('startDate'), True, False, _arrangement(info))
            if job:
                job['employer_board'] = employer
                jobs.append(job)
    result = SourceRecords(jobs, {'listed_records': listed, 'title_candidates': len(candidates),
                                  'detail_failures': failed, 'truncated': truncated,
                                  'search_terms': list(terms)})
    if failed:
        result.diagnostics['failed_details'] = failed
    if issue:
        result.diagnostics['partial_error'] = issue
    return result


def cache_key(url, body):
    """POSTs share one URL, so the cache key must include the request body."""
    return url + '#' + quote(json.dumps(body, sort_keys=True))
