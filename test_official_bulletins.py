"""Offline tests for bounded official NEOGOV bulletin retrieval and reranking.

No real network requests or private résumé material are used here.
"""
import unittest
from official_bulletins import (
    official_bulletin_url, parse_bulletin_html, fetch_official_bulletin,
    enrich_priority_government_jobs
)
from posting_requirements import extract_posting_requirements
from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index

RESUME = (
    'Group newspaper publisher, operations director, 25 years in business '
    'management, responsible for P&L, regional budgets and forecasts. '
    'Supervised department managers, negotiated major vendors and contracts, '
    'led distribution logistics, community partnerships and revenue growth.'
)
SUMMARY = (
    'Oversee teams, business processes, large budgets, staff, fleet, '
    'strategic priorities and contracts. '*8
)
FULL = (
    '<html><header><h1>Transmission Section Manager (Mgr 3)</h1></header>'
    '<main><h2>Position Description</h2>'
    '<p>Lead managers across water operations. Manage operating budgets, '
    'fiscal accountability, staffing, procurement and strategic planning. '
    'Oversee distribution system maintenance and repair processes.</p>'
    '<h2>Qualifications</h2><p>Experience: Five (5) years of experience '
    'in a water distribution/transmission system or treatment plant, '
    'including supervisory experience.</p>'
    '<p>License, Certification, and Other Requirements: Current Water '
    'Distribution Management III certification or ability to obtain '
    'WDM III within twelve (12) months of hire date.</p>'
    '<h2>Desired Qualifications</h2>'
    '<p>Preferred: familiarity with asset management and '
    'water distribution systems.</p>'
    '<h2>Additional Information</h2>'
    '<p>This position is required to work in person at the facility.</p>'
    '<p>Public utilities provide community water and treatment programs '
    'across the region; the role supports reliable access to drinking water.</p>'
    '</main><footer>Copyright GovernmentJobs</footer></html>'
)
URL='https://www.governmentjobs.com/careers/seattle/jobs/5491625-0/transmission-section-manager'
SCHOOL='https://www.schooljobs.com/careers/mydistrict/jobs/5485240-0/operations-manager'


class _FakeResponse:
    def __init__(self,body,url):
        self.body=body.encode('utf-8')
        self.url=url
        self.headers={'Content-Type':'text/html; charset=utf-8'}
    def geturl(self):
        return self.url
    def read(self,n):
        return self.body[:n]
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False


class OfficialBulletinTests(unittest.TestCase):
    def job(self, **options):
        return {
            'title':'Transmission Section Manager (Mgr 3)',
            'source':'NEOGOV',
            'company':'City of Seattle',
            'url':URL,
            'description':SUMMARY,
            **options
        }

    def test_only_existing_provider_vacancy_url_creates_print_lookup(self):
        self.assertEqual(official_bulletin_url(URL),
                         'https://www.governmentjobs.com/careers/seattle/jobs/newprint/5491625')
        self.assertEqual(official_bulletin_url(SCHOOL),
                         'https://www.schooljobs.com/careers/mydistrict/jobs/newprint/5485240')
        self.assertEqual(official_bulletin_url('https://example.org/jobs/5491625'),'')
        self.assertEqual(official_bulletin_url('https://www.governmentjobs.com/careers/seattle/jobs'),'')
        self.assertEqual(official_bulletin_url('http://www.governmentjobs.com/careers/seattle/jobs/5491625'),'')

    def test_full_bulletin_has_verified_title_and_qualification_section(self):
        desc=parse_bulletin_html(FULL,'Transmission Section Manager (Mgr 3)')
        self.assertIn('Qualifications',desc)
        self.assertIn('Five (5) years',desc)
        self.assertIn('Desired Qualifications',desc)
        self.assertNotIn('Copyright GovernmentJobs',desc)
        self.assertEqual(parse_bulletin_html('<html><h1>Jobs portal</h1></html>',
                                             'Transmission Section Manager'),'')
        self.assertEqual(parse_bulletin_html(FULL,'Unrelated Finance Director'),'')

    def test_fetch_accepts_official_html_and_rejects_redirect_outside_provider(self):
        def good(req,timeout=7):
            return _FakeResponse(FULL,req.full_url)
        desc=fetch_official_bulletin(self.job(),opener=good)
        self.assertIn('water distribution/transmission',desc)
        def redirect(req,timeout=7):
            return _FakeResponse(FULL,'https://unrelated.example.org/')
        self.assertEqual(fetch_official_bulletin(self.job(),opener=redirect),'')

    def test_enriches_only_eligible_top_candidate_and_avoids_mutating_cached(self):
        government=self.job()
        unrelated={'title':'Partnership Manager','company':'Example Media',
                   'source':'Workable employer','url':'https://apply.workable.com/j/ABCDEFG',
                   'description':SUMMARY}
        raw=[government,unrelated]
        calls=[]
        def fetch(job):
            calls.append(job['url'])
            return parse_bulletin_html(FULL,job['title'])
        enriched,stats=enrich_priority_government_jobs(raw,raw,fetch=fetch,limit=1)
        self.assertEqual(calls,[URL])
        self.assertEqual(stats['full_bulletins'],1)
        self.assertIn('Five (5)',enriched[0]['description'])
        self.assertEqual(raw[0]['description'],SUMMARY)
        self.assertEqual(enriched[0]['description_source'],'Official full public job bulletin')
        self.assertIn('Employer posting',enriched[1]['description_source'])

    def test_failed_lookup_keeps_summary_and_incomplete_provenance(self):
        raw=[self.job()]
        output,stats=enrich_priority_government_jobs(raw,raw,fetch=lambda j:'')
        self.assertEqual(stats['full_bulletins'],0)
        self.assertEqual(stats['summary_only'],1)
        self.assertIn('summary only',output[0]['description_source'].casefold())

    def test_required_water_field_under_qualifications_and_desired_not_required(self):
        desc=parse_bulletin_html(FULL,'Transmission Section Manager')
        report=extract_posting_requirements(
            {'title':'Transmission Section Manager','description':desc},RESUME)
        fields={c['area']:c for c in report['checks']}
        water=fields['Water utilities / transmission operations']
        self.assertTrue(water['priority'].startswith('Required'))
        self.assertGreater(water['ranking_caution'],0)
        credential=fields['Water operator certification']
        self.assertIn('obtained later',credential['priority'])
        self.assertLessEqual(credential['ranking_caution'],6)

    def test_bulletin_minimums_downrank_generic_high_overlap(self):
        profile=compile_resume_profile(RESUME,())
        summary=self.job(description_source='RSS summary only — important requirements may be missing')
        full=self.job(description=parse_bulletin_html(FULL,'Transmission Section Manager'),
                      description_source='Official full public job bulletin')
        a=assess_job_qualifications(summary,profile,RESUME)
        b=assess_job_qualifications(full,profile,RESUME)
        self.assertLessEqual(evidence_index(a),82)
        self.assertTrue(b['posting_requirement_checks'])
        self.assertTrue(any(c['area']=='Water utilities / transmission operations'
                            and c['ranking_caution']>0
                            for c in b['posting_requirement_checks']))
        self.assertLess(evidence_index(b),90)

    def test_good_transferable_role_stays_uncapped_with_full_description(self):
        job={'title':'Operations Manager',
             'description_source':'Official full public job bulletin',
             'description':('Position Description\n'+SUMMARY+
                '\nQualifications\nExperience: five years managing '
                'budgets, teams, revenue growth, and vendor contracts.')}
        q=assess_job_qualifications(job,compile_resume_profile(RESUME,()),RESUME)
        self.assertFalse(any(x['ranking_caution'] for x in
                             q['posting_requirement_checks']))
        self.assertGreaterEqual(evidence_index(q),60)


if __name__=='__main__':
    unittest.main()
