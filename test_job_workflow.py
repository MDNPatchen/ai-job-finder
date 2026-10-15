"""No-network regressions for job identifiers, salaries, filters and history."""
import unittest
from job_workflow import (
    canonical_job_url, distinct_posting_key, posting_id, annotate_new_results,
    salary_lower_bound, seniority_label, preferences_allow
)


def job(url='https://example.org/jobs/101',location='Fargo, ND',
        title='Operations Director',company='Example Media',salary=''):
    return {'url':url,'location':location,'title':title,
            'company':company,'salary':salary,'work_style':'Hybrid','date':'2026-10-15'}


class JobWorkflowTests(unittest.TestCase):
    def test_different_cities_same_title_kept(self):
        self.assertNotEqual(distinct_posting_key(job()),distinct_posting_key(
            job(url='https://example.org/jobs/102',location='Bismarck, ND')))

    def test_same_city_different_requisitions_kept(self):
        self.assertNotEqual(distinct_posting_key(job()),
                            distinct_posting_key(job(url='https://example.org/jobs/103')))

    def test_identical_url_cross_provider_is_same_posting(self):
        self.assertEqual(posting_id(job()),posting_id(job(
            url='https://www.example.org/jobs/101?utm_medium=email',
            location='North Dakota (multiple offices)')))

    def test_actual_query_id_is_not_discarded(self):
        a=job(url='https://example.org/jobs?jobId=1234')
        b=job(url='https://example.org/jobs?jobId=5678')
        self.assertNotEqual(posting_id(a),posting_id(b))

    def test_generic_city_job_index_falls_back_to_location(self):
        a=job(url='https://cityjobs.nyc.gov/jobs',location='Brooklyn, NY')
        b=job(url='https://cityjobs.nyc.gov/jobs',location='Queens, NY')
        self.assertNotEqual(posting_id(a),posting_id(b))

    def test_non_http_url_is_not_identity(self):
        self.assertEqual(canonical_job_url('javascript:alert(1)'),'')

    def test_same_posting_tracking_url_normalizes(self):
        self.assertEqual(canonical_job_url('https://example.com/job/7?utm_source=newsletter&gclid=x'),
                         canonical_job_url('http://www.example.com/job/7'))

    def test_first_search_only_establishes_baseline(self):
        jobs,seen=annotate_new_results([job()],[],False)
        self.assertFalse(jobs[0]['new_since_last_search'])
        self.assertEqual(len(seen),1)

    def test_second_search_marks_only_unknown_postings(self):
        first,seen=annotate_new_results([job()],[],False)
        second,more=annotate_new_results([job(),
                job(url='https://example.org/jobs/200')],seen,True)
        self.assertFalse(second[0]['new_since_last_search'])
        self.assertTrue(second[1]['new_since_last_search'])
        self.assertEqual(len(more),2)

    def test_salary_parses_annual_k_and_full_dollars(self):
        self.assertEqual(salary_lower_bound('$110k–$140k Annually'),110000)
        self.assertEqual(salary_lower_bound('$95,000 - $124,000'),95000)

    def test_never_invent_annual_salary_from_hourly(self):
        self.assertIsNone(salary_lower_bound('$90/hour'))
        self.assertIsNone(salary_lower_bound('Salary not listed'))

    def test_unknown_compensation_can_be_included_or_excluded(self):
        j=job()
        self.assertTrue(preferences_allow(j,['ND'],{
            'minimum_salary':120000,'include_unlisted_salary':True}))
        self.assertFalse(preferences_allow(j,['ND'],{
            'minimum_salary':120000,'include_unlisted_salary':False}))

    def test_state_include_and_exclude(self):
        j=job()
        self.assertFalse(preferences_allow(j,['ND'],{'included_states':['MN']}))
        self.assertFalse(preferences_allow(j,['ND'],{'excluded_states':['ND']}))
        self.assertTrue(preferences_allow(j,['ND'],{'included_states':['ND']}))

    def test_seniority_filter(self):
        self.assertEqual(seniority_label('Regional Publisher'),'Publisher')
        self.assertEqual(seniority_label('Chief Operating Officer'),'Executive / VP')
        self.assertEqual(seniority_label('Regional Operations Director'),'Director')
        self.assertFalse(preferences_allow(job(),['ND'],{'seniority':['Publisher']}))

    def test_unspecified_work_arrangement_only_excluded_when_selected(self):
        j=job()
        j['work_style']='Not specified'
        self.assertTrue(preferences_allow(j,['ND'],{}))
        self.assertFalse(preferences_allow(j,['ND'],
                                           {'verified_workplace_only':True}))


if __name__=='__main__':
    unittest.main()
