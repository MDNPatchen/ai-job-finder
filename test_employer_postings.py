"""No-network tests for direct employer job screening."""
import unittest
from employer_postings import (
    is_recruiter_employer, is_individual_vacancy_url,
    is_foreign_location, posting_quality,
)

class EmployerPostingTests(unittest.TestCase):
    def test_known_search_firms_and_recruiter_names_are_excluded(self):
        for company in (
            'Keller Executive Search', 'HOA Talent', 'Jobot',
            'Beacon Hill Staffing', 'Some Recruitment Agency',
            'National Executive Search',
        ):
            with self.subTest(company=company):
                self.assertTrue(is_recruiter_employer(company))
        for company in ('Future Publishing','KIPP','State of Iowa','Mayo Clinic'):
            self.assertFalse(is_recruiter_employer(company))

    def test_individual_employer_and_public_agency_job_links(self):
        for url in (
            'https://apply.workable.com/j/DB19968E49',
            'https://jobs.smartrecruiters.com/KIPP/744000155047480-director',
            'https://www.governmentjobs.com/careers/iowa/jobs/5500841-0',
            'https://jobs.ashbyhq.com/imprint/380d0eda-6a3d-40cc-85b5-62d8bd64b933',
            'https://job-boards.greenhouse.io/forbes/jobs/5436636008',
            'https://jobs.lever.co/morningbrew/1234-abcd',
            'https://www.usajobs.gov/job/807000000',
            'https://jobs.example.com/jobs?jobId=12345',
        ):
            with self.subTest(url=url):
                self.assertTrue(is_individual_vacancy_url(url))

    def test_directory_pages_and_bad_urls_not_shown_by_default(self):
        for url in (
            'https://cityjobs.nyc.gov/jobs',
            'https://www1.nyc.gov/jobs/get-started.page',
            'https://www.governmentjobs.com/careers/iowa',
            'https://jobs.ashbyhq.com/imprint',
            'https://apply.workable.com/jobs',
            'https://example.com/careers',
            'javascript:alert(1)',
        ):
            with self.subTest(url=url):
                self.assertFalse(is_individual_vacancy_url(url))

    def test_canadian_locations_do_not_parse_as_california(self):
        self.assertTrue(is_foreign_location('Toronto, ON, CA'))
        self.assertTrue(is_foreign_location('Vancouver, BC, Canada'))
        self.assertFalse(is_foreign_location('Sacramento, CA, United States'))
        self.assertFalse(is_foreign_location('Fargo, ND'))

    def test_direct_source_not_a_claim_of_employer_verification(self):
        self.assertEqual(posting_quality({
            'company':'Keller Executive Search',
            'source':'Workable employer',
            'url':'https://apply.workable.com/j/DB19968E49',
            'location':'Missouri City, Missouri',
        }), {'recruiter':True,'direct_source':True,
              'individual_url':True,'foreign_location':False})
        self.assertFalse(posting_quality({
            'company':'Unknown','source':'Arbeitnow',
            'url':'https://example.com/jobs/42',
            'location':'Fargo, ND',
        })['direct_source'])

if __name__=='__main__':
    unittest.main()
