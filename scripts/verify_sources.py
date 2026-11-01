"""Live check of public career boards: does each id return real US postings?

Usage:
    python scripts/verify_sources.py scripts/source_candidates.json
    python scripts/verify_sources.py job_sources.json        # health of the live catalog

A board PASSES only when its public API answers and returns at least one
posting that demonstrably belongs to that employer (for government feeds, the
vacancy URL must carry the same agency slug). Results print one line per board
and are also emitted as GitHub notice annotations so they can be read from
the check run. Network access is required; this is not part of the unit tests.
"""
import json
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from government_feed_identity import official_vacancy_agency  # noqa: E402

UA = {'User-Agent': 'AIJobFinder source verification (personal career research)'}


def _get(url, accept='application/json'):
    with urlopen(Request(url, headers={**UA, 'Accept': accept}), timeout=20) as response:
        return response.read(15_000_000)


def _json(url):
    return json.loads(_get(url))


def check_rss(provider, entry):
    host = 'www.governmentjobs.com' if provider == 'neogov' else 'www.schooljobs.com'
    source = 'NEOGOV' if provider == 'neogov' else 'NEOED Schooljobs'
    raw = _get(f'https://{host}/SearchEngine/JobsFeed?' + urlencode({'agency': entry['id']}),
               'application/rss+xml, application/xml')
    root = ET.fromstring(raw)
    items = [i for i in root.iter() if str(i.tag).rsplit('}', 1)[-1] == 'item']
    own = [i for i in items
           if official_vacancy_agency((i.findtext('link') or '').strip(), source) == entry['id'].lower()]
    detail = ''
    if own:
        fields = {str(c.tag).rsplit('}', 1)[-1]: (c.text or '').strip()
                  for c in own[0] if (c.text or '').strip()}
        detail = ' / '.join(fields.get(k, '') for k in ('location', 'department', 'title') if fields.get(k))
    return len(own), f'{len(items)} feed items; first: {detail[:110]}'


def check_greenhouse(entry):
    board = _json('https://boards-api.greenhouse.io/v1/boards/' + quote(entry['id']))
    jobs = _json('https://boards-api.greenhouse.io/v1/boards/' + quote(entry['id']) + '/jobs').get('jobs') or []
    return len(jobs), 'board name: ' + str(board.get('name', ''))[:80]


def check_lever(entry):
    rows = _json('https://api.lever.co/v0/postings/' + quote(entry['id']) + '?mode=json&limit=100')
    rows = rows if isinstance(rows, list) else []
    url = rows[0].get('hostedUrl', '') if rows else ''
    return len(rows), 'first: ' + str(url)[:100]


def check_ashby(entry):
    data = _json('https://api.ashbyhq.com/posting-api/job-board/' + quote(entry['id']))
    jobs = data.get('jobs') or []
    url = jobs[0].get('jobUrl', '') if jobs else ''
    return len(jobs), 'first: ' + str(url)[:100]


def check_smartrecruiters(entry):
    data = _json('https://api.smartrecruiters.com/v1/companies/' + quote(entry['id']) +
                 '/postings?' + urlencode({'limit': 10, 'destination': 'PUBLIC', 'country': 'us'}))
    rows = data.get('content') or []
    company = (rows[0].get('company') or {}).get('name', '') if rows else ''
    # Unknown company ids answer 200 with zero results, so require postings.
    return int(data.get('totalFound') or 0), 'company: ' + str(company)[:80]


def check_workable(entry):
    data = _json('https://www.workable.com/api/accounts/' + quote(entry['id']))
    return len(data.get('jobs') or []), 'account name: ' + str(data.get('name', ''))[:80]


CHECKS = {
    'neogov': lambda e: check_rss('neogov', e),
    'neoed': lambda e: check_rss('neoed', e),
    'greenhouse': check_greenhouse,
    'lever': check_lever,
    'ashby': check_ashby,
    'smartrecruiters': check_smartrecruiters,
    'workable': check_workable,
}


def run(path):
    catalog = json.loads(Path(path).read_text(encoding='utf-8'))
    tasks = [(provider, entry) for provider in CHECKS for entry in catalog.get(provider, [])]

    def one(task):
        provider, entry = task
        for attempt in range(3):
            try:
                count, detail = CHECKS[provider](entry)
                status = 'PASS' if count > 0 else 'EMPTY'
                break
            except HTTPError as exc:
                count, detail, status = 0, f'HTTP {exc.code}', 'FAIL'
                if exc.code not in (429, 500, 502, 503, 504):
                    break
            except (URLError, OSError, ValueError, ET.ParseError) as exc:
                count, detail, status = 0, type(exc).__name__ + ': ' + str(exc)[:80], 'FAIL'
                if not isinstance(exc, (URLError, TimeoutError, OSError)):
                    break
            time.sleep(3 * (attempt + 1))  # timeouts are usually rate limits; back off
        return {'provider': provider, 'id': entry['id'], 'name': entry['name'],
                'state': entry.get('state', ''), 'status': status, 'postings': count, 'detail': detail}

    # Government feeds share one host, so query it gently; other APIs in parallel.
    rss = [t for t in tasks if t[0] in ('neogov', 'neoed')]
    api = [t for t in tasks if t[0] not in ('neogov', 'neoed')]
    with ThreadPoolExecutor(max_workers=2) as slow, ThreadPoolExecutor(max_workers=8) as fast:
        rss_results = slow.map(one, rss)
        api_results = fast.map(one, api)
        results = list(rss_results) + list(api_results)
    return results


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'scripts/source_candidates.json'
    label = Path(path).stem  # tags every line so mixed annotations stay readable
    results = run(path)
    lines = [f"{label}|{r['status']}|{r['provider']}|{r['id']}|{r['name']}|{r['state']}|{r['postings']}|{r['detail']}"
             for r in results]
    for line in lines:
        print(line)
    passed = sum(r['status'] == 'PASS' for r in results)
    print(f'SUMMARY {passed}/{len(results)} passed')
    # GitHub limits annotations per step, so pack results into a few notices.
    chunk, size = [], 0
    chunks = []
    for line in lines:
        if size + len(line) > 45000:  # GitHub caps notices per job; keep them few
            chunks.append(chunk)
            chunk, size = [], 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        chunks.append(chunk)
    for n, part in enumerate(chunks, 1):
        body = '%0A'.join(x.replace('%', '%25').replace('\r', '').replace('\n', ' ') for x in part)
        print(f'::notice title={label} {n}/{len(chunks)}::{body}')
    print(f'::notice title={label} summary::{passed}/{len(results)} passed')


if __name__ == '__main__':
    main()
