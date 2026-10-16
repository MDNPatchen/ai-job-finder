"""Version 3.1.11 overlap-scoring regressions (synthetic employer postings).

Tests distinguish duplicated *experience* cautions from separate degree,
license, residency and internal-application rules. Never assert eligibility.
"""
import unittest

from specialist_caution_calibration import calibrate_cautions
from qualification_matcher import compile_resume_profile,assess_job_qualifications
from ranked_breakdowns import evidence_index, breakdowns_json, breakdowns_csv_rows
from transfer_fit import transfer_fit

RESUME=(
    "Group Newspaper Publisher and Regional Operations Director with 25 years "
    "of operating businesses in multiple locations. Managed annual P&L, "
    "financial budgets, employees, departments, senior teams, contracts, "
    "vendors, procurement, newspaper distribution, community partnerships, "
    "marketing, sales and operational planning. Earned Bachelor's degree "
    "in Business Administration."
)
DUTIES=(
    "Lead multi-site operational performance, staff and senior leadership "
    "teams, annual P&L and budgets, strategic planning, contracts, vendors, "
    "distribution logistics, marketing, community partnerships, "
    "procurement and revenue growth. " * 5
)
CONSTRUCTION=(
    "<h2>Qualifications</h2>"
    "<li>Bachelor's degree in Construction Management, Engineering or "
    "Architecture is required.</li>"
    "<li>At least eight years of experience managing commercial or "
    "industrial construction projects is required.</li>"
    "<h2>Responsibilities</h2>"+DUTIES
)


def score(title,description,resume=RESUME):
    job={'title':title,'description':description}
    return assess_job_qualifications(
        job,compile_resume_profile(resume,()),resume)


class ExperienceOverlapCalibrationTests(unittest.TestCase):
    def test_construction_triple_coverage_one_experience_penalty(self):
        r=calibrate_cautions(
            [{'area':'Construction / engineering operations',
              'ranking_caution':23,'needs_verification':True}],
            [{'area':'Construction project / preconstruction leadership',
              'ranking_caution':24,'reason':'Verify field'}],
            [{'area':'Construction / preconstruction delivery experience',
              'type':'Field-specific experience','ranking_caution':25,
              'priority':'Required / minimum','listing_excerpt':'8 years'},
             {'area':'Bachelor degree in technical/professional field',
              'type':'Education / professional credential',
              'ranking_caution':22,'priority':'Required / minimum',
              'listing_excerpt':"Bachelor's degree in Construction Management"}])
        self.assertEqual(r['domain_penalty'],0)
        self.assertEqual(r['career_penalty'],0)
        self.assertEqual(r['posting_penalty'],47) # experience 25 PLUS degree 22
        self.assertEqual(r['overlap_relief'],47) # domain 23 + title 24
        self.assertEqual(r['posting_checks'][0]['applied_ranking_caution'],25)
        self.assertEqual(r['posting_checks'][1]['applied_ranking_caution'],22)
        self.assertEqual(r['career_cautions'][0]['ranking_caution'],24)
        self.assertEqual(r['career_cautions'][0]['applied_ranking_caution'],0)
        self.assertTrue(r['specialist_gap'])

    def test_separate_fields_remain_independent(self):
        r=calibrate_cautions(
            [{'area':'Construction / engineering operations','ranking_caution':23}],
            [{'area':'Dedicated corporate finance / investment analysis',
              'ranking_caution':22}],
            [{'area':'Construction / preconstruction delivery experience',
              'type':'Field-specific experience','ranking_caution':25},
             {'area':'Professional license / registration',
              'type':'Education / professional credential',
              'ranking_caution':22},
             {'area':'Internal applicants only',
              'type':'Application eligibility','ranking_caution':50}])
        self.assertEqual(r['domain_penalty'],0)
        self.assertEqual(r['career_penalty'],22)
        self.assertEqual(r['posting_penalty'],65) # deliberate existing category cap
        self.assertTrue(any(x['applied_ranking_caution']==50
                            for x in r['posting_checks']))

    def test_career_only_same_domain_counts_once(self):
        r=calibrate_cautions(
            [{'area':'Construction / engineering operations','ranking_caution':23}],
            [{'area':'Construction project / preconstruction leadership','ranking_caution':24}],
            [])
        self.assertEqual(r['career_penalty'],24)
        self.assertEqual(r['domain_penalty'],0)
        self.assertEqual(r['overlap_relief'],23)

    def test_genuine_other_career_stage_and_degree_not_removed(self):
        r=calibrate_cautions([],[
            {'area':'Coordination / administrative career stage to review',
             'ranking_caution':17},
            {'area':'Construction project / preconstruction leadership',
             'ranking_caution':24},
        ],[
            {'area':'Construction / preconstruction delivery experience',
             'type':'Field-specific experience','ranking_caution':25},
            {'area':'Bachelor degree in technical/professional field',
             'type':'Education / professional credential','ranking_caution':22}
        ])
        self.assertEqual(r['career_penalty'],17)
        self.assertEqual(r['posting_penalty'],47)
        self.assertEqual(r['overlap_relief'],24)

    def test_no_clean_transfer_bonus_when_specialist_gap_is_in_other_layer(self):
        qualification={
            'resume_present':True,'resume_matches':[
                {'area':'Operations leadership','match_origin':'Job description'},
                {'area':'Financial & P&L leadership','match_origin':'Job description'},
                {'area':'Negotiation & vendor management','match_origin':'Job description'},
            ],'confirmed_only':[],'not_documented':[]
        }
        job={'description':DUTIES}
        unflagged=transfer_fit(qualification,job,80,0,0,
                               specialist_gap=False)
        flagged=transfer_fit(qualification,job,80,0,0,
                             specialist_gap=True)
        self.assertEqual(unflagged['index']-flagged['index'],9)


class RealisticExportCases(unittest.TestCase):
    def test_managers_keep_transferable_evidence_without_ignoring_education(self):
        for title in ('Senior Capital Project Manager',
                      'Senior Construction Project Manager'):
            with self.subTest(title=title):
                q=score(title,CONSTRUCTION)
                self.assertGreater(q['duty_coverage_index'],35)
                self.assertGreater(evidence_index(q),0)
                self.assertLess(evidence_index(q),80)
                self.assertGreater(q['ranking_overlap_relief'],0)
                self.assertTrue(any(
                    x['type']=='Education / professional credential'
                    and x['ranking_caution']>0
                    and x['applied_ranking_caution']>0
                    for x in q['posting_requirement_checks']))
                self.assertTrue(any(
                    x['type']=='Field-specific experience'
                    and x['ranking_caution']>0
                    and x['applied_ranking_caution']>0
                    for x in q['posting_requirement_checks']))
                self.assertEqual(q['career_fit_penalty'],0)
                self.assertTrue(any(
                    x['ranking_caution']>0
                    for x in q['career_fit_cautions']))

    def test_no_general_evidence_can_still_score_zero(self):
        q=score('Senior Construction Project Manager',
                CONSTRUCTION,resume="I have some clerical experience.")
        self.assertEqual(evidence_index(q),0)

    def test_corporate_finance_no_double_count_but_still_needs_proof(self):
        desc=(
            "<h2>Qualifications</h2><li>Five to ten years of professional "
            "experience in corporate finance and FP&A required.</li>"
            "<h2>Responsibilities</h2>"+DUTIES
        )
        q=score('Manager, Corporate Finance',desc)
        self.assertGreater(q['ranking_overlap_relief'],0)
        self.assertGreater(q['posting_requirement_penalty'],0)
        self.assertTrue(any(
            x['area']=='Corporate finance / FP&A specialization'
            and x['applied_ranking_caution']>0
            for x in q['posting_requirement_checks']))

    def test_unrelated_operations_leadership_ranking_stable(self):
        q=score('Regional Operations Director',DUTIES)
        self.assertEqual(q['ranking_overlap_relief'],0)
        self.assertEqual(q['career_fit_penalty'],0)
        self.assertEqual(q['posting_requirement_penalty'],0)

    def test_both_exports_explain_overlap_and_requirements(self):
        job={'title':'Senior Construction Project Manager',
             'company':'Example Employer',
             'description':CONSTRUCTION,
             'source':'Employer Careers',
             'url':'https://example.org/jobs/123'}
        q=score(job['title'],job['description'])
        job['qualification_match']=q
        data=breakdowns_json([job])[0]
        csv=breakdowns_csv_rows([job])[0]
        self.assertEqual(data['overlapping_specialist_deductions_avoided'],
                         q['ranking_overlap_relief'])
        self.assertEqual(csv['Overlapping specialist deductions avoided (points)'],
                         q['ranking_overlap_relief'])
        self.assertIn('Bachelor degree',csv['Employer minimum requirements to verify'])
        self.assertIn('experience',data['ranking_caution_calibration'])


if __name__=="__main__":
    unittest.main()
