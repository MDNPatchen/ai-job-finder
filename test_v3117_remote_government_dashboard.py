"""3.1.17: public-sector remote exception and real inset dashboard layout.

Tests exercise the actual extracted production filter without network access.
Government RSS company+agency URL validation is applied before remote exception.
"""
import unittest
from pathlib import Path
from job_workflow import permitted_remote_source
from test_ranked_breakdowns import extracted_filter,make_job
from ui_theme import APP_CSS

def remote(title,source,company,url,government=False,style='Remote'):
    j=make_job(title=title,source=source,company=company,rank=18)
    j.update({'url':url,'work_style':style,'remote':style=='Remote',
              'government':government,'eligible':True,
              'arrangement_source':'Employer ATS workplace label'})
    return j


class RemotePublicSectorTests(unittest.TestCase):
    def test_mayo_remote_allowed(self):
        j=remote('Senior Project Manager (Remote)','Mayo Clinic','Mayo Clinic',
                 'https://jobs.mayoclinic.org/job/rochester/job/33647/123456')
        self.assertTrue(permitted_remote_source(j))
        matches,_=extracted_filter()([j],None,'On-site + Hybrid','','')
        self.assertEqual(len(matches),1)

    def test_official_neogov_remote_allowed(self):
        j=remote('Budget Director (Remote)','NEOGOV','City of Boise',
                 'https://www.governmentjobs.com/careers/boiseid/jobs/5504395-budget-director',True)
        self.assertTrue(permitted_remote_source(j))
        out,_=extracted_filter()([j],None,'On-site + Hybrid','','')
        self.assertEqual(len(out),1,out)
        self.assertEqual(out[0]['work_style'],'Remote')

    def test_neogov_title_remote_recovers_mislabeled_workplace(self):
        j=remote('Deputy Manager (Remote)','NEOGOV','City of Boise',
                 'https://www.governmentjobs.com/careers/boiseid/jobs/5504395-deputy',True,
                 style='Not specified')
        out,_=extracted_filter()([j],None,'On-site + Hybrid','','')
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['work_style'],'Remote')
        self.assertIn('title',out[0]['arrangement_source'])

    def test_nyc_open_data_remote_allowed(self):
        j=remote('Program Director (Remote)','NYC Open Data','NYC Agency',
                 'https://cityjobs.nyc.gov/jobs/1899',True)
        out,_=extracted_filter()([j],None,'On-site + Hybrid','','',
                                listing_scope='All sources (including directory links)')
        self.assertEqual(len(out),1)

    def test_private_remote_stays_excluded(self):
        j=remote('Operations Director (Remote)','Greenhouse','Private Inc',
                 'https://jobs.example.com/remote-100',False)
        self.assertFalse(permitted_remote_source(j))
        out,exc=extracted_filter()([j],None,'On-site + Hybrid','','')
        self.assertEqual(len(out),0)
        self.assertEqual(exc['location'],1)

    def test_private_feed_does_not_gain_exception_by_claiming_government(self):
        j=remote('Director (Remote)','Greenhouse','Private Inc',
                 'https://jobs.example.com/remote-101',True)
        self.assertFalse(permitted_remote_source(j))
        self.assertEqual(extracted_filter()([j],None,'On-site + Hybrid','','')[0],[])

    def test_neogov_without_verified_company_and_agency_is_excluded(self):
        j=remote('Operations Director (Remote)','NEOGOV','Unverified Public Employer',
                 'https://www.governmentjobs.com/careers/boiseid/jobs/5504395-operations',True)
        out,exc=extracted_filter()([j],None,'On-site + Hybrid','','')
        self.assertEqual(out,[])
        self.assertEqual(exc['eligibility'],1)

    def test_boolean_government_flag_required(self):
        j=remote('Operations Director (Remote)','NEOGOV','City of Boise',
                 'https://www.governmentjobs.com/careers/boiseid/jobs/5504395-operations',False)
        self.assertFalse(permitted_remote_source(j))

    def test_strict_workplace_filters_exclude_remote_even_government(self):
        j=remote('Chief Analyst (Remote)','NEOGOV','City of Boise',
                 'https://www.governmentjobs.com/careers/boiseid/jobs/5504395-analyst',True)
        f=extracted_filter()
        for style in ('On-site only','Hybrid only'):
            with self.subTest(style=style):
                self.assertEqual(f([j],None,style,'','')[0],[])

    def test_hybrid_still_allowed_for_private_and_government(self):
        private=remote('Publisher','Greenhouse','Private Inc',
                       'https://jobs.example.com/hybrid',False,style='Hybrid')
        government=remote('Agency Manager','NEOGOV','City of Boise',
            'https://www.governmentjobs.com/careers/boiseid/jobs/5504395-agency',True,
            style='Hybrid')
        out,_=extracted_filter()([private,government],None,'Hybrid only','','')
        self.assertEqual(len(out),2)


class DashboardInsetTests(unittest.TestCase):
    def test_native_dashboard_container_used(self):
        src=Path(__file__).with_name('app.py').read_text()
        self.assertIn("st.container(border=False, key='dashboard_content')",src)
        self.assertEqual(src.count("st.columns(3, gap='large')"),2)

    def test_actual_streamlit_rail_selector_has_symmetric_inset(self):
        self.assertIn('[data-testid="stMainBlockContainer"]',APP_CSS)
        self.assertIn('.block-container',APP_CSS)
        self.assertIn('width:calc(100% - 8rem)',APP_CSS)
        self.assertIn('padding:2rem 3rem 4rem',APP_CSS)
        self.assertIn('margin-left:auto!important;margin-right:auto!important',APP_CSS)
        self.assertIn('.st-key-dashboard_content',APP_CSS)
        self.assertIn('padding:1rem 1.55rem 1.8rem',APP_CSS)
        self.assertIn('column-gap:1.35rem!important',APP_CSS)

    def test_mobile_inset_remains_responsive(self):
        self.assertIn('@media(max-width:900px)',APP_CSS)
        self.assertIn('width:100%!important;max-width:100%!important',APP_CSS)
        self.assertNotIn('border-left:4px',APP_CSS)
        self.assertNotIn('border-top:3px',APP_CSS)


if __name__=='__main__':
    unittest.main()
