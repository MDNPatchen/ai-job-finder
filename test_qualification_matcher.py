"""Offline, free regression checks for grounded qualification matching."""
import unittest
from qualification_matcher import (
    compile_resume_profile, assess_job_qualifications, _qualification_screeners
)


class QualificationMatcherTests(unittest.TestCase):
    def setUp(self):
        self.resume = (
            "Publisher, 2002-present\n"
            "Led multiple publications with full P&L responsibility.\n"
            "Managed annual budgets and forecasting, improved revenue.\n"
            "Oversaw distribution logistics and delivery routes.\n"
            "Negotiated contracts with vendors and supervised managers.\n"
        )
        self.profile = compile_resume_profile(self.resume, ())

    def test_matches_quote_resume_text(self):
        job = {'title': 'Regional Operations Director',
               'description': 'Manage multi-site operations, financial budgets, logistics and vendors.'}
        check = assess_job_qualifications(job, self.profile, self.resume)
        self.assertGreaterEqual(len(check['resume_matches']), 3)
        self.assertTrue(any(
            'budgets' in ' '.join(x['resume_evidence']) for x in check['resume_matches']))
        self.assertNotIn('Healthcare administration',
                         [x['area'] for x in check['resume_matches']])

    def test_confirmed_experience_separate_from_resume(self):
        profile = compile_resume_profile(
            'I worked as a publisher.', ('Healthcare administration',))
        check = assess_job_qualifications(
            {'title': 'Hospital Operations Director',
             'description': 'Healthcare administration and hospital management.'},
            profile, 'I worked as a publisher.')
        self.assertIn('Healthcare administration',
                      [x['area'] for x in check['confirmed_only']])
        self.assertNotIn('Healthcare administration',
                         [x['area'] for x in check['resume_matches']])

    def test_missing_resume_text_is_not_disqualification(self):
        check = assess_job_qualifications(
            {'title': 'Hospital Director',
             'description': 'Hospital management and healthcare administration.'},
            self.profile, self.resume)
        self.assertTrue(check['not_documented'])
        self.assertNotIn('unqualified', check['label'].lower())

    def test_flags_degree_license_and_experience_duration(self):
        description = (
            "Required: Current RN license. Minimum 8 years of leadership experience. "
            "Bachelor's degree required.")
        checks = _qualification_screeners(description, self.resume)
        self.assertEqual({r['type'] for r in checks},
                         {'Education', 'License / certification', 'Experience duration'})
        self.assertTrue(all('Not verified' in r['resume_status'] for r in checks))

    def test_years_must_be_explicit_in_resume(self):
        r = _qualification_screeners('Minimum 7 years of related experience required.',
                                     'Over 12 years of management experience.')
        self.assertIn('mentions at least', r[0]['resume_status'])

    def test_no_resume_means_no_documented_matches(self):
        profile = compile_resume_profile('', ('Operations leadership',))
        check = assess_job_qualifications(
            {'title': 'Operations Director',
             'description': 'Operations management.'}, profile, '')
        self.assertIn('Upload', check['label'])
        self.assertEqual(check['resume_matches'], [])

    def test_empty_job_details_do_not_invent_requirements(self):
        check = assess_job_qualifications(
            {'title': 'General Manager', 'description': ''}, self.profile, self.resume)
        self.assertEqual(check['screeners'], [])

    def test_resume_quotes_and_job_excerpts_are_present(self):
        check = assess_job_qualifications(
            {'title': 'Finance Director',
             'description': 'Responsible for annual budgets, vendor contracts, and financial oversight.'},
            self.profile, self.resume)
        for item in check['resume_matches']:
            self.assertTrue(item['listing_excerpt'])
            self.assertTrue(item['resume_evidence'])

    def test_manual_confirmation_does_not_create_resume_excerpt(self):
        profile = compile_resume_profile(self.resume, ('Healthcare administration',))
        self.assertIn('Healthcare administration', profile['confirmed'])
        self.assertNotIn('Healthcare administration', profile['evidence'])


if __name__ == '__main__':
    unittest.main()
