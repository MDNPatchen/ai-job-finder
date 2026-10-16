"""Offline employer-minimum regressions, including examples of old score inflation.

These are synthetic vacancy snippets, not a claim that any live vacancy is
still open. Neither the ranking nor the flags establish actual eligibility.
"""
import unittest
from posting_requirements import extract_posting_requirements
from qualification_matcher import assess_job_qualifications, compile_resume_profile
from ranked_breakdowns import breakdowns_csv_rows, evidence_index
from posting_metadata import strict_onsite_requirement, reconcile_workplace_record

RESUME=(
    'Group newspaper publisher and operations director, over 25 years '
    'of business leadership experience. Managed department managers, '
    'multi-site operations, P&L, budgets, finance forecasts, distribution, '
    'vendor contracts, community partnerships, revenue and strategy.'
)
COMMON=(
    'Manage staff, budgets, operations, contracts, vendor negotiations, '
    'community partnerships, leadership and financial reporting. '*7
)


def checks(title,desc=COMMON,resume=RESUME):
    return extract_posting_requirements({'title':title,'description':desc},resume)


def score(title,desc=COMMON,resume=RESUME):
    profile=compile_resume_profile(resume,())
    return assess_job_qualifications({'title':title,'description':desc},
                                     profile,resume)


class EmployerMinimumTests(unittest.TestCase):
    def test_in_house_only_in_title_not_top_general_result(self):
        normal=score('Division Area Office Coordinator', COMMON)
        restricted=score('Division Area Office Coordinator (IN-HOUSE ONLY)',COMMON)
        self.assertLess(evidence_index(restricted),evidence_index(normal))
        self.assertTrue(restricted['application_restricted'])
        self.assertGreaterEqual(restricted['posting_requirement_penalty'],45)
        x=checks('Coordinator (in-house only)')
        self.assertEqual(x['checks'][0]['type'],'Application eligibility')

    def test_external_applicants_are_not_blocked_by_false_internal_positive(self):
        out=checks('Operations Manager',
                   'Positions are open to both internal and external candidates. '+COMMON)
        self.assertFalse(out['application_restricted'])

    def test_boston_residency_is_not_claimed_from_management_background(self):
        out=checks('Finance & Operations Manager',
                   'Boston residency is required upon appointment. '+COMMON)
        self.assertGreater(out['ranking_caution'],0)
        self.assertTrue(any(x['type']=='Residency / location' for x in out['checks']))

    def test_water_utility_specific_experience_and_certification(self):
        desc=('Minimum qualifications: 6 years of experience in water '
              'transmission and water distribution operations. '
              'Applicant must possess a Grade IV water distribution '
              'manager certification. '+COMMON)
        out=checks('Transmission Section Manager',desc)
        areas={x['area'] for x in out['checks']}
        self.assertIn('Water utilities / transmission operations',areas)
        self.assertIn('Water operator certification',areas)
        self.assertGreaterEqual(out['ranking_caution'],30)
        specific=score('Transmission Section Manager',desc)
        generic=score('Regional Operations Manager',COMMON)
        self.assertLess(evidence_index(specific),evidence_index(generic))

    def test_ability_to_obtain_credential_is_not_mandatory_today(self):
        desc=('Minimum 5 years of water distribution experience. '
              'Candidate may obtain water distribution certification '
              'within 12 months after hiring. '+COMMON)
        out=checks('Transmission Manager',desc)
        cert=next(x for x in out['checks'] if x['area']=='Water operator certification')
        self.assertIn('obtained later',cert['priority'])
        self.assertLessEqual(cert['ranking_caution'],6)

    def test_required_ehs_background_beyond_generic_operations(self):
        desc=('Required 5 years of experience with environmental health '
              'and safety (EHS) and OSHA compliance in industrial settings. '+COMMON)
        out=checks('EHS Specialist',desc)
        self.assertTrue(any(x['area']=='Environmental health and safety / OSHA'
                            and x['ranking_caution']>0 for x in out['checks']))

    def test_portfolio_required_but_preferred_software_not_mandatory(self):
        desc=('Required: demonstrated product design experience, '
              'with a design portfolio showcasing UX design expertise. '
              'Figma skills preferred. '+COMMON)
        out=checks('Manager, Product Design',desc)
        self.assertTrue(any(x['area']=='Professional design portfolio'
                            and x['ranking_caution']>0 for x in out['checks']))

    def test_preferred_specialized_experience_zero_penalty(self):
        desc=('OSHA-30 certification preferred. '
              'Experience in water distribution preferred. '+COMMON)
        out=checks('Operations Manager',desc)
        self.assertEqual(out['ranking_caution'],0)

    def test_technical_role_without_evidence_does_not_imply_disqualification(self):
        q=score('Environmental Health & Safety Manager',
                'EHS experience is required. '+COMMON)
        self.assertTrue(q['posting_requirement_checks'])
        self.assertNotIn('unqualified',str(q).lower())

    def test_explicit_in_person_overrides_conflicting_hybrid_label(self):
        desc='This position is required to work in person. '+COMMON
        self.assertTrue(strict_onsite_requirement(desc))
        job={'description':desc,'work_style':'Hybrid','remote':False,
             'arrangement_source':'Employer ATS workplace label',
             'location':'Seattle, WA'}
        result=reconcile_workplace_record(job)
        self.assertEqual(result['work_style'],'On-site')
        self.assertIn('conflicts',result['arrangement_source'])
        self.assertTrue(result['workplace_conflict'])

    def test_hybrid_office_days_are_not_reclassified_as_full_onsite(self):
        desc='This is a hybrid work schedule. Must report in person twice each week.'
        self.assertFalse(strict_onsite_requirement(desc))
        job={'description':desc,'work_style':'Hybrid','remote':False,
             'arrangement_source':'Employer ATS workplace label'}
        self.assertEqual(reconcile_workplace_record(job)['work_style'],'Hybrid')

    def test_exports_explain_minimums_and_workplace_conflict(self):
        q=score('Office Coordinator (IN-HOUSE ONLY)', COMMON)
        job={'title':'Office Coordinator (IN-HOUSE ONLY)',
             'company':'Example School',
             'work_style':'On-site',
             'workplace_conflict':'Conflicting hybrid provider and in-person text.',
             'qualification_match':q}
        row=breakdowns_csv_rows([job])[0]
        self.assertIn('Internal applicants only',row['Employer minimum requirements to verify'])
        self.assertEqual(row['Posting explicitly restricts to internal applicants'],
                         'Yes — verify eligibility')
        self.assertIn('Conflicting hybrid',row['Workplace labeling conflict'])


if __name__=='__main__':
    unittest.main()
