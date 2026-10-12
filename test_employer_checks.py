"""Free/offline tests for employer checks; no live HTTP requests in test suite."""
import unittest
from datetime import date
from employer_checks import (
    normalized, check_posting_link, parse_gleif_response, exact_sec_filer,
    annual_usd, sec_metrics, sec_financials, check_employer
)


class EmployerBackgroundTests(unittest.TestCase):
    def setUp(self):
        self.job = {'company':'Mayo Clinic', 'source':'Mayo Clinic',
                    'url':'https://jobs.mayoclinic.org/job/rochester/example/33647/123',
                    'government':False}
        self.profiles = {'employers':[{
            'name':'Mayo Clinic','employer_type':'nonprofit',
            'history':{'year':1864,'meaning':'Origins of the medical practice, not incorporation',
                       'source_url':'https://history.mayoclinic.org/timelines/this-month-in-our-history/'},
            'references':[{'title':'IRS Form 990','url':'https://apps.irs.gov/app/eos/'}]
        }]}
        self.lei={'data':[{'attributes':{
            'lei':'5493001KJTIIGC8Y1R12',
            'entity':{'legalName':{'name':'Mayo Clinic'},'status':'ACTIVE',
                      'creationDate':'1914-03-06T00:00:00Z'}}}]}

    def test_normalized_legal_suffix(self):
        self.assertEqual(normalized('Example, Inc.'), normalized('EXAMPLE'))
        self.assertNotEqual(normalized('Example Holdings, Inc.'), normalized('Example'))

    def test_posting_page_200_is_not_claimed_as_confirmed_job(self):
        r=check_posting_link(self.job['url'],lambda u:(200,'jobs.mayoclinic.org'))
        self.assertEqual(r['status'],'Page responds')
        self.assertIn('does not confirm',r['detail'])

    def test_arbitrary_job_domain_not_accessed(self):
        r=check_posting_link('https://example.org/jobs',lambda u:self.fail('must not fetch untrusted host'))
        self.assertEqual(r['status'],'Not verified')

    def test_http_link_not_accessed(self):
        r=check_posting_link('http://jobs.mayoclinic.org/jobs',
                             lambda u:self.fail('must not fetch plain HTTP'))
        self.assertEqual(r['status'],'Not verified')

    def test_wrong_redirect_host_not_called_verified(self):
        r=check_posting_link(self.job['url'],lambda u:(200,'localhost'))
        self.assertEqual(r['status'],'Not verified')

    def test_lei_exact_match(self):
        r=parse_gleif_response(self.lei,'Mayo Clinic')
        self.assertEqual(r['creation_date'],'1914-03-06')
        self.assertEqual(r['status'],'ACTIVE')

    def test_lei_fuzzy_similar_name_not_matched(self):
        self.assertIsNone(parse_gleif_response(self.lei,'Mayo Business Holdings'))

    def test_lei_ambiguous_match_not_claimed(self):
        self.assertIsNone(parse_gleif_response({'data':self.lei['data']*2},'Mayo Clinic'))

    def test_sec_filer_exact(self):
        data={'0':{'title':'EXAMPLE, INC.','cik_str':1234,'ticker':'EXM'},
              '1':{'title':'EXAMPLE HOLDINGS, INC.','cik_str':5678,'ticker':'EXH'}}
        self.assertEqual(exact_sec_filer(data,'Example')['cik'],1234)
        self.assertIsNone(exact_sec_filer(data,'Example Group'))

    def test_fiscal_year_filing_not_quarter_and_same_year_duplicates(self):
        data={'units':{'USD':[
            {'form':'10-K','fp':'FY','start':'2025-01-01','end':'2025-12-31','filed':'2026-02-10','val':100},
            {'form':'10-K','fp':'FY','start':'2024-01-01','end':'2024-12-31','filed':'2025-02-10','val':90},
            {'form':'10-Q','fp':'Q1','start':'2026-01-01','end':'2026-03-31','filed':'2026-05-02','val':999},
            {'form':'10-K','fp':'FY','start':'2025-10-01','end':'2025-12-31','filed':'2026-02-11','val':999}]}}
        self.assertEqual([x['value'] for x in annual_usd(data)],[100,90])

    def test_negative_net_income_is_reported_without_health_grade(self):
        facts={'entityName':'Example Inc','facts':{'us-gaap':{
            'NetIncomeLoss':{'units':{'USD':[{'form':'10-K','fp':'FY','start':'2025-01-01',
                 'end':'2025-12-31','filed':'2026-02-15','val':-5000000}]}}
        }}}
        result=sec_metrics(facts,1234,'Example Inc')
        self.assertEqual(result['metrics'][0]['recent']['value'],-5000000)
        self.assertNotIn('safe',str(result).lower())

    def test_sec_contact_optional_not_an_api_key(self):
        r=sec_financials('Example',getter=lambda *a,**kw:self.fail('No secret supplied'))
        self.assertEqual(r['status'],'Not checked')

    def test_mayo_roots_and_nonprofit_reports(self):
        result=check_employer(self.job,self.profiles,today=date(2026,10,11),
          posting_fetch=lambda u:(200,'jobs.mayoclinic.org'),
          gleif_getter=lambda u:self.lei,
          sec_getter=lambda *a,**kw:self.fail('Nonprofit should not use SEC'))
        self.assertEqual(result['age']['years'],162)
        self.assertIn('not incorporation',result['age']['meaning'])
        self.assertEqual(result['identity']['entity_status'],'ACTIVE')
        self.assertEqual(result['identity']['status'],'Exact-name GLEIF legal entity match')
        self.assertTrue(result['references'])
        self.assertIn('Nonprofit',result['financial']['status'])

    def test_government_does_not_require_private_registries(self):
        job={'company':'Minnesota County','source':'NEOGOV','government':True,
             'url':'https://www.governmentjobs.com/careers/example/jobs/123'}
        result=check_employer(job,{},posting_fetch=lambda u:(200,'www.governmentjobs.com'),
            gleif_getter=lambda *a,**kw:self.fail('Government should skip registry'),
            sec_getter=lambda *a,**kw:self.fail('Government should skip SEC'))
        self.assertIn('Government',result['financial']['status'])

    def test_no_age_when_no_verified_source(self):
        result=check_employer(self.job,{},posting_fetch=lambda u:(200,'jobs.mayoclinic.org'),
            gleif_getter=lambda u:{'data':[]})
        self.assertIsNone(result['age'])

if __name__ == '__main__':
    unittest.main()
