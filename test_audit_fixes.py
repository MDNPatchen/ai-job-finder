"""Offline regressions from the user's October 2026 ranked-job audit.

All postings here are synthetic; no actual user resume or export is committed.
"""
import ast
from pathlib import Path
import unittest

from posting_metadata import (
    affirmative, declared_arrangement, from_explicit_description,
    greenhouse_workplace_label, employer_identity_kind)
from qualification_domains import identify_specialized_requirements
from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index, breakdowns_csv_rows, breakdowns_json


RESUME = (
    'Group Newspaper Publisher and Operations Director: 25 years of progressive management experience.\n'
    'Managed multi-site newspaper operations, budgets, and P&L.\n'
    'Led distribution logistics, negotiated vendor contracts, and supervised managers.\n'
    'Oversaw strategic planning, advertising revenues, and KPI reports.\n'
)


def qualification(title, description):
    return assess_job_qualifications(
        {'title':title,'description':description},
        compile_resume_profile(RESUME,()),RESUME)


def critical_area(q, name):
    return next((s for s in q.get('specialized_requirements', [])
                 if s['area']==name), None)


class JobAuditRegressionTests(unittest.TestCase):
    def test_hr_generalist_required_specific_years(self):
        q=qualification('HOA/COA Director of Operations',
                        'What We Are Looking For (Required): 5+ years of HR generalist experience, '
                        'including onboarding, offboarding and employee relations. '
                        'Also manage the website, budgets and community outreach.')
        r=critical_area(q,'Human resources / employee relations')
        self.assertIsNotNone(r)
        self.assertTrue(r['needs_verification'])
        self.assertIn('Required',r['priority'])
        self.assertLess(evidence_index(q),85)

    def test_school_operations_preferred_not_mislabeled_required(self):
        q=qualification('Director of Operations',
                        'Manage school budgets and enrollment. 2+ years experience '
                        'in K-12 school operations strongly preferred; teaching a plus.')
        r=critical_area(q,'K-12 / school operations')
        self.assertIsNotNone(r)
        self.assertEqual(r['priority'],'Preferred experience')
        self.assertLess(r['ranking_caution'],12)

    def test_kipp_managing_director_school_operations_preferred_experience(self):
        q=qualification('Managing Director of School Operations, High Schools',
                        'Direct network school operations and lead teams. '
                        '5-10 years of work experience, preferably in business '
                        'or operations management. K-12 education experience '
                        "preferred. Bachelor's degree required; Master's degree "
                        'preferred. Manage school budgets and student enrollment.')
        k12=critical_area(q,'K-12 / school operations')
        self.assertIsNotNone(k12)
        self.assertTrue(k12['needs_verification'])
        self.assertEqual(k12['priority'],'Preferred experience')
        self.assertLess(k12['ranking_caution'],12)
        self.assertIn('K-12',k12['listing_excerpt'])
        self.assertLess(evidence_index(q),90)

    def test_kipp_school_operations_manager_role_is_flagged(self):
        q=qualification('School Operations Manager (26-27)',
                        'Manage facilities, school attendance and enrollment. '
                        'A minimum of two years in operations or education.')
        k12=critical_area(q,'K-12 / school operations')
        self.assertIsNotNone(k12)
        self.assertTrue(k12['needs_verification'])

    def test_newspaper_advertiser_school_mention_is_not_a_school_job(self):
        q=qualification('Regional Operations Director',
                        'Coordinate annual advertising with local schools and '
                        'manage newspaper budgets, printing and distribution.')
        self.assertIsNone(critical_area(q,'K-12 / school operations'))

    def test_food_handling_explicit_requirement(self):
        q=qualification('General Manager',
                        'Lead warehouse operations and food distribution. '
                        'Experience in food handling environments required. '
                        'Maintain compliance with SQF, HACCP, FSMA standards.')
        r=critical_area(q,'Food handling / safety / distribution')
        self.assertIsNotNone(r)
        self.assertGreaterEqual(r['ranking_caution'],20)

    def test_fuel_or_convenience_industry_years(self):
        q=qualification('Travel Center General Manager',
                        'Minimum of 3-5 years experience in a management role within '
                        'the fuel, convenience store, or hospitality industries.')
        r=critical_area(q,'Fuel retail / convenience stores')
        self.assertIsNotNone(r)
        self.assertIn('Required',r['priority'])
        self.assertLess(evidence_index(q),85)

    def test_restaurant_title_requires_domain_review(self):
        q=qualification('General Manager (Sbarro)',
                        'Manage shifts, food safety, staff training and inventory.')
        self.assertIsNotNone(
            critical_area(q,'Food handling / safety / distribution'))
        self.assertLess(evidence_index(q),82)

    def test_construction_years_not_substituted_by_publisher_years(self):
        q=qualification('Director of Operations - Construction Services',
                        'Who you are: 10+ years of progressive construction experience '
                        'with responsibility for construction operations, project estimates '
                        'and managing field teams.')
        r=critical_area(q,'Construction / engineering operations')
        self.assertIsNotNone(r)
        self.assertTrue(r['needs_verification'])
        self.assertGreaterEqual(r['ranking_caution'],20)

    def test_enterprise_sales_years_industry_caution(self):
        q=qualification('Vice President of Business Development',
                        'Looking for 10–15 years of enterprise B2B sales, '
                        'consultative solution selling and large new-logo deals.')
        r=critical_area(q,'Enterprise B2B sales / quota management')
        self.assertIsNotNone(r)
        self.assertTrue(r['needs_verification'])
        self.assertGreaterEqual(r['ranking_caution'],20)

    def test_publisher_operations_director_keeps_competitive_fit(self):
        q=qualification('Director of Operations',
                        'Drive operational improvements, lead managers, oversee '
                        'budgets, negotiate vendor contracts and manage KPIs.')
        self.assertFalse(q['specialized_requirements'])
        self.assertGreater(evidence_index(q),70)

    def test_incidental_domain_terms_do_not_create_formal_requirements(self):
        q=qualification('Director of Operations',
                        'Coordinate with restaurant customers and HR on logistics. '
                        'Own budget planning and vendor negotiations.')
        self.assertFalse(q['specialized_requirements'])

    def test_black_bear_diner_requires_specific_restaurant_experience(self):
        q=qualification('General Manager (Black Bear Diner)',
                        'Requirements: Minimum of 3-5 years of management '
                        'experience in a full-service restaurant or diner environment. '
                        'Must oversee food safety, teams and profit margins.')
        restaurant=critical_area(q,'Restaurant / food-service management')
        self.assertIsNotNone(restaurant)
        self.assertTrue(restaurant['needs_verification'])
        self.assertIn('Required',restaurant['priority'])
        self.assertLess(evidence_index(q),85)

    def test_assistant_black_bear_diner_uses_casual_dining_context(self):
        q=qualification('Assistant General Manager (Black Bear Diner)',
                        'Full-service, casual dining, or high-volume restaurant '
                        'experience strongly preferred. Managing shifts, staff, '
                        'guest service, food safety and budget reporting.')
        restaurant=critical_area(q,'Restaurant / food-service management')
        self.assertIsNotNone(restaurant)
        self.assertEqual(restaurant['priority'],'Preferred experience')
        self.assertLess(restaurant['ranking_caution'],12)

    def test_yugo_student_housing_residential_requirements(self):
        q=qualification('Assistant General Manager',
                        'As an Assistant General Manager at a student housing '
                        'community you will oversee day-to-day property management '
                        'operations. A minimum of one year of experience, preferably '
                        'in residential properties, rental operations, or related '
                        'business operations is required. Support lease renewals, '
                        'resident accounts, rent collections, and leasing activities.')
        residential=critical_area(q,'Property / residential operations')
        self.assertIsNotNone(residential)
        self.assertTrue(residential['needs_verification'])
        self.assertTrue(residential['ranking_caution']>0)
        # The employer accepts related business operations, so do not falsely
        # call residential experience itself an absolute prerequisite.
        self.assertIn(residential['priority'],(
            'Preferred experience',
            'Required / experience stated — verify exact wording'))
        self.assertLess(evidence_index(q),90)

    def test_residential_duties_without_experience_clause_still_warn(self):
        q=qualification('General Manager',
                        'Lead resident accounts, collect rent payments, '
                        'support lease renewals and oversee property operations.')
        residential=critical_area(q,'Property / residential operations')
        self.assertIsNotNone(residential)
        self.assertIn(residential['priority'],(
            'Role responsibility — verify relevant experience',
            'Experience mentioned — review full posting'))
        self.assertLessEqual(residential['ranking_caution'],10)

    def test_incidental_diner_mention_does_not_trigger_nonrestaurant_role(self):
        q=qualification('Director of Operations',
                        'Coordinate deliveries with a diner client. '
                        'Oversee publication logistics and advertising contracts.')
        self.assertIsNone(critical_area(q,'Restaurant / food-service management'))

    def test_generic_publisher_job_is_not_residential_management(self):
        q=qualification('Regional Operations Director',
                        'Direct branch operations and vendor contracts. '
                        'Build community partnerships and manage budgets.')
        self.assertIsNone(critical_area(q,'Property / residential operations'))

    def test_career_years_do_not_verify_construction_years(self):
        q=qualification('Director of Operations – Construction Services',
                        'Minimum 10+ years of construction experience required.')
        self.assertTrue(q['specialized_requirements'])
        self.assertIn('not documented',q['specialized_requirements'][0]['resume_status'])


class PostingMetadataTests(unittest.TestCase):
    def test_provider_work_styles(self):
        self.assertEqual(declared_arrangement('ONSITE'),'On-site')
        self.assertEqual(declared_arrangement('on_site'),'On-site')
        self.assertEqual(declared_arrangement('HYBRID'),'Hybrid')
        self.assertEqual(declared_arrangement('Remote'),'Remote')
        self.assertEqual(declared_arrangement('unavailable'),'')

    def test_unknown_city_is_not_on_site(self):
        self.assertEqual(from_explicit_description('Role based in Salt Lake City, UT.'),'')
        self.assertEqual(from_explicit_description('Work arrangement: Hybrid.'),'Hybrid')
        self.assertEqual(from_explicit_description('This is an on-site position.'),'On-site')

    def test_remote_negative_not_falsely_remote(self):
        self.assertEqual(from_explicit_description('This role is not fully remote.'),'')
        self.assertEqual(from_explicit_description('This is a fully remote role.'),'Remote')

    def test_workable_false_string_is_false(self):
        self.assertFalse(affirmative('false'))
        self.assertFalse(affirmative('0'))
        self.assertTrue(affirmative('true'))

    def test_greenhouse_metadata_only_with_labeled_field(self):
        self.assertEqual(greenhouse_workplace_label([
            {'name':'Workplace type','value':'Hybrid'}]),'Hybrid')
        self.assertEqual(greenhouse_workplace_label([
            {'name':'Work locations','value':'Hybrid'}]),'')

    def test_recruiter_not_verified_hiring_client(self):
        self.assertIn('intermediary',employer_identity_kind('Keller Executive Search'))
        self.assertIn('intermediary',employer_identity_kind('HOA Talent'))
        self.assertNotIn('intermediary',employer_identity_kind('Mayo Clinic'))

    def test_csv_header_and_employer_origin_consistency(self):
        q=qualification('Director of Operations',
                        'Lead operational efficiency, budgets and reporting.')
        job={'title':'Director of Operations','company':'Keller Executive Search',
             'source':'Workable employer','location':'Denver, CO','date':'2026-10-10',
             'url':'https://apply.workable.com/j/synthetic-test',
             'work_style':'Hybrid', 'arrangement_source':'Employer ATS workplace label',
             'employer_identity_kind':employer_identity_kind('Keller Executive Search'),
             'qualification_match':q}
        row=breakdowns_csv_rows([job])[0]
        self.assertIn('Comparative fit index (0-96; not hiring probability)',row)
        self.assertNotIn('Evidence overlap index (0-100, not hiring probability)',row)
        self.assertIn('intermediary',row['Employer identification'])
        self.assertEqual(row['Work arrangement evidence'],'Employer ATS workplace label')
        detailed=breakdowns_json([job])[0]
        self.assertEqual(detailed['comparative_fit_index'],detailed['evidence_match_index'])


if __name__=='__main__':
    unittest.main()
