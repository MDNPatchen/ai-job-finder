"""Find employers' public Workday job boards (network; run on GitHub Actions).

For each candidate: read its careers pages for links to *.myworkdayjobs.com,
then try likely tenant/site addresses. A board counts only when Workday's
public job API answers with a positive job total. Results print one line per
employer and as compact GitHub notices.
"""
import json
import re
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UA = {'User-Agent': 'Mozilla/5.0 (AIJobFinder source discovery; personal career research)'}
LINK = re.compile(r'https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)', re.I)

def load_candidates():
    """Candidates from scripts/workday_candidates.json, minus tenants already cataloged."""
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / 'scripts' / 'workday_candidates.json').read_text(encoding='utf-8'))
    known = {e['id'].lower() for e in json.loads((root / 'job_sources.json').read_text(encoding='utf-8')).get('workday', [])}
    out = []
    for c in data['candidates']:
        if any(t.lower() in known for t in c['tenants']):
            continue
        out.append((c['name'], c.get('pages', []), c['tenants']))
    return out


WD = ('wd1', 'wd5', 'wd3', 'wd12', 'wd501', 'wd503', 'wd108', 'wd10')


def site_guesses(tenant):
    t = tenant
    cap = t[:1].upper() + t[1:]
    return ('External', 'Careers', 'External_Careers', 'Search', f'{t}', f'{t}careers', f'{t}-careers',
            f'{cap}Careers', f'{cap}_Careers', f'{t.upper()}', 'jobs', 'en-US')


def fetch(url, data=None):
    headers = {**UA, 'Accept': 'application/json, text/html'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    with urlopen(Request(url, data=data, headers=headers), timeout=15) as r:
        return r.read(3_000_000)


def total_jobs(tenant, wd, site):
    url = f'https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs'
    body = json.dumps({'limit': 1, 'offset': 0, 'searchText': '', 'appliedFacets': {}}).encode()
    try:
        data = json.loads(fetch(url, body))
        return int(data.get('total') or 0)
    except (HTTPError, URLError, OSError, ValueError):
        return -1


def discover(candidate):
    name, pages, tenants = candidate
    found = set()
    for page in pages:
        try:
            html = fetch(page).decode('utf-8', 'replace')
            for tenant, wd, site in LINK.findall(html):
                if site.lower() not in ('wday', 'en-us'):
                    found.add((tenant.lower(), wd.lower(), site))
        except (HTTPError, URLError, OSError, ValueError):
            pass
    hits = [(t, wd, s, total_jobs(t, wd, s)) for t, wd, s in sorted(found)]
    hits = [h for h in hits if h[3] > 0]
    if not hits:
        for tenant in tenants:
            for wd in WD:
                for site in site_guesses(tenant):
                    n = total_jobs(tenant, wd, site)
                    if n > 0:
                        hits.append((tenant, wd, site, n))
                        break
                if hits:
                    break
            if hits:
                break
    how = 'page link' if found and hits and (hits[0][0], hits[0][1], hits[0][2]) in found else 'guess'
    return name, hits[:1], how, len(found)


def main():
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(discover, load_candidates()))
    lines = []
    for name, hits, how, links in results:
        if hits:
            t, wd, s, n = hits[0]
            lines.append(f'FOUND|{name}|{t}|{wd}|{s}|{n}|{how}')
        else:
            lines.append(f'NONE|{name}|links_on_page={links}')
    for line in lines:
        print(line)
    found = [l for l in lines if l.startswith('FOUND')]
    none = [l.split('|')[1] for l in lines if l.startswith('NONE')]
    chunks, cur = [], ''
    for line in found:
        if len(cur) + len(line) > 3500:
            chunks.append(cur)
            cur = ''
        cur += line + '%0A'
    if cur:
        chunks.append(cur)
    for i, c in enumerate(chunks, 1):
        print(f'::notice title=workday found {i}/{len(chunks)}::{c}')
    print('::notice title=workday none::' + ', '.join(none)[:3500])


if __name__ == '__main__':
    main()
