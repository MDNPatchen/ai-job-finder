"""On-demand, evidence-based employer background checks. No paid services.

A working posting page does not prove legitimacy. An LEI identifies a legal
entity, not the author of an advert. SEC figures do not certify solvency.
All uncertain details remain explicitly unverified.
"""
import json
import re
import ssl
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler, HTTPSHandler

APP_UA = "AIJobFinder/1.0 (https://github.com/MDNPatchen/ai-job-finder)"
APPROVED_HOSTS = frozenset((
    'www.governmentjobs.com','governmentjobs.com','www.schooljobs.com',
    'schooljobs.com','boards.greenhouse.io','job-boards.greenhouse.io',
    'jobs.lever.co','jobs.ashbyhq.com','apply.workable.com',
    'jobs.smartrecruiters.com','jobs.mayoclinic.org','cityjobs.nyc.gov',
    'www.arbeitnow.com'))


def normalized(name):
    s = re.sub(r'[^a-z0-9]+', ' ', str(name or '').casefold()).strip()
    return ' '.join(re.sub(r'\b(incorporated|inc|corporation|corp|limited|ltd|llc|plc)\b', '', s).split())


def public_json(url, user_agent=APP_UA, timeout=8, limit=12000000):
    request = Request(url, headers={'User-Agent':user_agent, 'Accept':'application/json'})
    with urlopen(request, timeout=timeout) as response:
        data = response.read(limit+1)
    if len(data) > limit:
        raise ValueError('Registry response exceeds size limit')
    return json.loads(data)


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urlparse(newurl)
        if p.scheme != 'https' or (p.hostname or '').lower() not in APPROVED_HOSTS:
            raise ValueError('Posting redirects outside approved career-site hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def check_posting_link(url, fetch=None):
    """A server response proves only that the URL responded; not that a job is open."""
    url = str(url or '')
    p = urlparse(url)
    host = (p.hostname or '').lower()
    out = {'url':url, 'hostname':host or 'Unknown', 'status':'Not verified',
           'detail':'', 'vacancy_status':'Open status not established', 'platform':'Posting URL supplied by source'}
    if p.scheme != 'https' or host not in APPROVED_HOSTS:
        out['detail'] = 'This domain is not in the small approved automated-check list. Open the posting directly to verify the employer.'
        return out
    out['platform'] = ('Mayo-branded careers domain' if host == 'jobs.mayoclinic.org'
                       else 'Recognized public recruiting platform')
    try:
        if fetch is not None:
            code, final_host = fetch(url)
        else:
            req = Request(url, headers={'User-Agent':'Mozilla/5.0 (personal career research)',
                                        'Accept':'text/html,*/*','Range':'bytes=0-4095'})
            opener = build_opener(SafeRedirect(),
                                  HTTPSHandler(context=ssl.create_default_context()))
            with opener.open(req, timeout=7) as response:
                code = response.getcode()
                final_host = (urlparse(response.geturl()).hostname or '').lower()
                page=response.read(65536).decode('utf-8','replace')
                if re.search(r'\b(?:this (?:job|position|vacancy) (?:is no longer available|has been filled|has closed)|job posting (?:has expired|is closed))\b',page,re.I):
                    out['vacancy_status']='Posting explicitly says closed or unavailable'
        if code in (200,206) and final_host in APPROVED_HOSTS:
            out['status']='Page responds'
            out['detail']='The career URL responded. This does not confirm the role is open or independently authenticate the hiring employer.'
        else:
            out['detail']='No verifiable response from the approved career-site host.'
    except HTTPError as exc:
        if exc.code in (404,410): out['vacancy_status']='Posting unavailable (HTTP '+str(exc.code)+')'
        out['detail']=('The posting returned HTTP 404/410; it may have been removed.'
                       if exc.code in (404,410) else f'The posting could not be checked (HTTP {exc.code}).')
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        out['detail']='The posting could not be checked (' + type(exc).__name__ + ').'
    return out


def parse_gleif_response(payload, employer):
    exact = []
    for record in (payload.get('data') or [])[:20]:
        attr=record.get('attributes') or {}
        entity=attr.get('entity') or {}
        name=entity.get('legalName') or {}
        legal_name=name.get('name') if isinstance(name,dict) else str(name)
        if not legal_name or normalized(legal_name)!=normalized(employer):
            continue
        lei=attr.get('lei') or record.get('id') or ''
        creation=str(entity.get('creationDate') or '')[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', creation):
            creation=''
        exact.append({'legal_name':legal_name,'lei':lei,
                      'status':entity.get('status') or 'Not specified',
                      'creation_date':creation,
                      'url':('https://search.gleif.org/#/record/'+lei
                             if re.fullmatch(r'[A-Z0-9]{20}',lei) else 'https://search.gleif.org/'),
                      'source':'GLEIF legal entity record'})
    return exact[0] if len(exact)==1 else None


def gleif_entity(name, getter=public_json):
    if not name or len(name)>150 or '·' in name:
        return None
    url='https://api.gleif.org/api/v1/lei-records?'+urlencode(
        {'filter[entity.legalName]':name,'page[size]':20})
    return parse_gleif_response(getter(url),name)


def exact_sec_filer(ticker_data, employer):
    matches=[]
    for row in (ticker_data.values() if isinstance(ticker_data,dict) else []):
        if not isinstance(row,dict) or normalized(row.get('title'))!=normalized(employer):
            continue
        try:
            matches.append({'cik':int(row['cik_str']),'name':row['title'],
                            'ticker':str(row.get('ticker') or '')})
        except (ValueError,TypeError,KeyError):
            pass
    return matches[0] if len(matches)==1 else None


def annual_usd(concept, instantaneous=False):
    data=((concept or {}).get('units') or {}).get('USD') or []
    items=[]
    for row in data:
        if row.get('form') not in ('10-K','10-K/A') or row.get('fp')!='FY':
            continue
        start,end=row.get('start'),row.get('end')
        if not end or not isinstance(row.get('val'),(int,float)):
            continue
        if instantaneous and start:
            continue
        if not instantaneous:
            if not start: continue
            try:
                days=(date.fromisoformat(end)-date.fromisoformat(start)).days
            except ValueError:
                continue
            if not 325<=days<=385:continue
        try:
            year=date.fromisoformat(end).year
        except ValueError:
            continue
        items.append({'year':year,'period_end':end,
                      'filed':row.get('filed') or '', 'value':row['val']})
    items.sort(key=lambda r:(r['period_end'],r['filed']),reverse=True)
    unique=[]
    for x in items:
        if x['year'] not in [r['year'] for r in unique]:
            unique.append(x)
        if len(unique)==2:break
    return unique


def sec_metrics(facts, cik, expected_name):
    concepts=(('Revenue',('RevenueFromContractWithCustomerExcludingAssessedTax',
                           'Revenues','SalesRevenueNet',
                           'RevenueFromContractWithCustomerIncludingAssessedTax'),False),
              ('Net income',('NetIncomeLoss',),False),
              ('Operating cash flow',('NetCashProvidedByUsedInOperatingActivities',),False),
              ('Total assets',('Assets',),True),
              ('Total liabilities',('Liabilities',),True),
              ('Cash and equivalents',('CashAndCashEquivalentsAtCarryingValue',),True))
    gaap=(facts.get('facts') or {}).get('us-gaap') or {}
    metrics=[]
    for label,tags,instant in concepts:
        options=[]
        for tag in tags:
            rows=annual_usd(gaap.get(tag),instant)
            if rows:options.append((rows[0]['period_end'],tag,rows))
        if options:
            _,tag,rows=max(options,key=lambda x:x[0])
            metrics.append({'label':label,'tag':tag,
                            'recent':rows[0],'prior':rows[1] if len(rows)>1 else None})
    return {'entity_name':facts.get('entityName') or expected_name,
            'url':f'https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json',
            'metrics':metrics}


def sec_financials(company, sec_contact_email='', getter=public_json):
    """Only check filings when the user supplies a SEC-compliant contact email."""
    email=str(sec_contact_email or '').strip()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
        return {'status':'Not checked',
                'note':'For automatic, free SEC financial figures, optionally set SEC_CONTACT_EMAIL in Streamlit Secrets. No API key required.'}
    agent=f'AIJobFinder/1.0 ({email})'
    try:
        index=getter('https://www.sec.gov/files/company_tickers.json',user_agent=agent)
        match=exact_sec_filer(index,company)
        if not match:
            return {'status':'No exact SEC filer identified',
                    'note':'SEC ticker data did not yield an unambiguous legal-name match. This does not imply financial trouble.'}
        cik=match['cik']
        facts=getter(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',user_agent=agent)
        if normalized(facts.get('entityName')) != normalized(match['name']):
            return {'status':'SEC name conflict',
                    'note':'SEC reported a different legal entity; its financial numbers were withheld.'}
        result=sec_metrics(facts,cik,match['name'])
        return {'status':'SEC annual metrics found' if result['metrics'] else 'SEC filer found; comparable figures absent',
                'ticker':match['ticker'],'filer':result,
                'note':'Figures are historical, annual SEC disclosures for the exact matched filer, not a credit rating or a promise that its hiring subsidiary is financially secure.'}
    except (HTTPError,URLError,TimeoutError,ValueError,OSError) as exc:
        return {'status':'SEC lookup unavailable',
                'note':'The public SEC service could not be checked ('+type(exc).__name__+').'}


def check_employer(job,profiles,sec_contact_email='',posting_fetch=None,
                   gleif_getter=public_json,sec_getter=public_json,today=None):
    today=today or date.today()
    company=str(job.get('company') or '').strip()
    profiles_by_name={str(x.get('name') or '').casefold():x
                      for x in profiles.get('employers',[])}
    profile=profiles_by_name.get(company.casefold()) or {}
    out={'company':company,'source':job.get('source') or 'Unspecified',
         'posting':check_posting_link(job.get('url'),posting_fetch),
         'identity':None,'age':None,'financial':None,'references':[],
         'checked_at':datetime.now(timezone.utc).isoformat(),
         'warning':'Posting accessibility, age, an LEI record, and historical financial filings do not certify legitimacy, solvency, or continued hiring.'}
    if profile.get('employer_type'):out['employer_type']=profile['employer_type']
    hist=profile.get('history') or {}
    try:
        year=int(hist['year'])
        if 1700<=year<=today.year and str(hist.get('source_url') or '').startswith('https://'):
            out['age']={'since_year':year,'years':today.year-year,
                        'meaning':hist.get('meaning') or 'Historical origins',
                        'source_url':hist['source_url'],
                        'note':'Historical origins are not the incorporation date of the current legal entity.'}
    except (ValueError,KeyError,TypeError):
        pass
    for ref in profile.get('references',[]):
        if isinstance(ref,dict) and str(ref.get('url') or '').startswith('https://'):
            out['references'].append({'title':str(ref.get('title') or 'Source'),
                                      'url':ref['url']})
    if job.get('government'):
        out['identity']={'status':'Government employer named by job source',
                         'note':'The feed attributes this listing to a public agency. Independent identity confirmation is incomplete.'}
        out['financial']={'status':'Government budget review needed',
                          'note':'Agency finances depend on appropriations and public budgets, not company earnings. Review the agency budget and job notice.'}
        return out
    try:
        gleif=gleif_entity(company,gleif_getter)
        if gleif:
            out['identity']={**gleif,'entity_status':gleif.get('status'),
                             'status':'Exact-name GLEIF legal entity match',
                             'note':'An LEI identifies a reported legal entity, not the person posting this particular vacancy.'}
            if not out['age'] and gleif.get('creation_date'):
                try:
                    d=date.fromisoformat(gleif['creation_date'])
                    age=today.year-d.year-((today.month,today.day)<(d.month,d.day))
                    if age>=0:
                        out['age']={'since_year':d.year,'years':age,
                                    'meaning':'GLEIF recorded entity creation date',
                                    'source_url':gleif['url'],
                                    'note':'The LEI date is not a continuous-trading guarantee.'}
                except ValueError:pass
        else:
            out['identity']={'status':'No exact legal entity match',
                             'note':'GLEIF returned no unambiguous exact-name match. Many legitimate employers lack LEIs or use different legal names.'}
    except (HTTPError,URLError,TimeoutError,ValueError,OSError) as exc:
        out['identity']={'status':'Registry unavailable',
                         'note':'GLEIF could not be checked ('+type(exc).__name__+').'}
    if profile.get('employer_type')=='nonprofit':
        out['financial']={'status':'Nonprofit reports require review',
                          'note':'Review IRS Form 990 and published audited statements. These are not automatic guarantees of financial strength.'}
    else:
        out['financial']=sec_financials(company,sec_contact_email,sec_getter)
    return out
