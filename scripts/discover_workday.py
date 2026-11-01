"""Find employers' public Workday job boards (network; run on GitHub Actions).

For each candidate: read its careers pages for links to *.myworkdayjobs.com,
then try likely tenant/site addresses. A board counts only when Workday's
public job API answers with a positive job total. Results print one line per
employer and as compact GitHub notices.
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UA = {'User-Agent': 'Mozilla/5.0 (AIJobFinder source discovery; personal career research)'}
LINK = re.compile(r'https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)', re.I)

CANDIDATES = [
    # name, careers pages to scan, tenant guesses
    ('Avera Health', [], ['avera']),
    ('Sanford Health', ['https://www.sanfordhealth.org/careers', 'https://careers.sanfordhealth.org/'], ['sanfordhealth', 'sanford']),
    ('Essentia Health', ['https://www.essentiacareers.org/'], ['essentiahealth', 'essentia']),
    ('Trinity Health (Minot)', ['https://www.trinityhealth.org/careers/'], ['trinityhealthnd']),
    ('Altru Health System', ['https://www.altru.org/careers'], ['altru']),
    ('Monument Health', ['https://monument.health/careers/'], ['monumenthealth', 'monument']),
    ('Billings Clinic', ['https://www.billingsclinic.com/careers/'], ['billingsclinic']),
    ('Bozeman Health', ['https://bozemanhealth.org/careers'], ['bozemanhealth']),
    ('CentraCare', ['https://www.centracare.com/careers/'], ['centracare']),
    ('Allina Health', ['https://www.allinahealth.org/careers'], ['allina', 'allinahealth']),
    ('Fairview Health Services', ['https://www.fairview.org/careers'], ['fairview']),
    ('HealthPartners', ['https://www.healthpartners.com/careers/'], ['healthpartners']),
    ('Marshfield Clinic Health System', ['https://www.marshfieldclinic.org/careers'], ['marshfieldclinic']),
    ('Xcel Energy', ['https://careers.xcelenergy.com/'], ['xcelenergy']),
    ('Otter Tail Corporation', ['https://www.ottertail.com/careers'], ['ottertail']),
    ('Great River Energy', ['https://greatriverenergy.com/careers/'], ['greatriverenergy']),
    ('Minnkota Power Cooperative', ['https://www.minnkota.com/careers/'], ['minnkota']),
    ('Bell Bank', ['https://www.bell.bank/careers'], ['bellbank']),
    ('Gate City Bank', ['https://www.gatecity.bank/careers/'], ['gatecitybank']),
    ('Bremer Bank', ['https://www.bremer.com/careers'], ['bremer']),
    ('Thrivent', ['https://www.thrivent.com/about-us/careers'], ['thrivent']),
    ('U.S. Bank', [], ['usbank']),
    ('Wells Fargo', [], ['wf']),
    ('3M', [], ['3m']),
    ('Target', [], ['target']),
    ('General Mills', ['https://careers.generalmills.com/'], ['generalmills']),
    ('Hormel Foods', ['https://www.hormelfoods.com/careers/'], ['hormel', 'hormelfoods']),
    ('CHS Inc.', ['https://www.chsinc.com/careers'], ['chsinc', 'chs']),
    ("Land O'Lakes", ['https://careers.landolakesinc.com/'], ['landolakes']),
    ('Polaris', ['https://www.polaris.com/en-us/careers/'], ['polaris']),
    ('Ecolab', [], ['ecolab']),
    ('Ameriprise Financial', [], ['ameriprise']),
    ('Gannett', ['https://www.gannett.com/careers/'], ['gannett']),
    ('Lee Enterprises', ['https://lee.net/careers/'], ['lee', 'leeenterprises']),
    ('Gray Media', ['https://gray.tv/careers'], ['gray', 'graytv', 'graymedia']),
    ('Nexstar Media Group', ['https://www.nexstar.tv/careers/'], ['nexstar']),
    ('Sinclair', ['https://sbgi.net/careers/'], ['sbgi', 'sinclair']),
    ('Hearst', ['https://www.hearst.com/careers'], ['hearst']),
    ('Forum Communications', ['https://www.forumcomm.com/careers'], ['forumcomm']),
    ('Townsquare Media', ['https://www.townsquaremedia.com/careers'], ['townsquaremedia']),
    ('Graham Media Group', ['https://www.grahammedia.com/careers/'], ['grahammedia']),
    ('University of Wyoming', ['https://www.uwyo.edu/hr/prospective/'], ['uwyo']),
    ('University of Montana', ['https://www.umt.edu/jobs/'], ['umt']),
    ('Montana State University', ['https://www.montana.edu/jobs/'], ['montanastate']),
    ('South Dakota State University', ['https://www.sdstate.edu/human-resources/jobs'], ['sdstate']),
    ('University of Minnesota', ['https://hr.umn.edu/Jobs'], ['umn']),
    ('American Red Cross', ['https://www.redcross.org/about-us/careers.html'], ['redcross']),
    ('Boys & Girls Clubs of America', ['https://www.bgca.org/about-us/careers'], ['bgca']),
    ('YMCA of the North', ['https://www.ymcanorth.org/careers'], ['ymcanorth']),
    ('Goodwill-Easter Seals Minnesota', ['https://www.goodwilleasterseals.org/careers'], ['goodwilleasterseals']),
]
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
        results = list(pool.map(discover, CANDIDATES))
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
