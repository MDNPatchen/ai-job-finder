"""Offline regression cases for inflated cross-industry job rankings.

Examples are synthetic and do not copy any applicant résumé or job export.
A missing résumé phrase is not a hiring eligibility judgment.
"""
import unittest

from career_fit_guardrails import evaluate_career_fit
from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index, breakdowns_csv_rows

RESUME = (
    "Senior regional publisher and operations director with more than 25 years "
    "of management experience.\n"
    "Managed multiple publications and department managers.\n"
    "Led regional operations, budgeting and full P&L accountability.\n"
    "Managed logistics, distribution, operations teams, vendor negotiation and contracts.\n"
    "Led strategic planning, revenue growth, marketing and community partnerships.\n"
)
GENERIC_DUTIES = (
    "Manage regional operations, staff, annual financial budgets, "
    "strategic planning, distribution logistics, vendor contracts, "
    "company reporting, stakeholder engagement and revenue growth. " * 5
)


def fitted(title, duties=GENERIC_DUTIES, resume=RESUME):
    p = compile_resume_profile(resume, ())
    job = {"title":title, "description":duties}
    return assess_job_qualifications(job, p, resume)


class CareerFitGuardrailTests(unittest.TestCase):
    def test_transferable_director_beats_technical_engineer_same_duties(self):
        broad=fitted("Regional Business Operations Manager")
        specific=fitted("Chief Building Engineer")
        self.assertGreater(evidence_index(broad), evidence_index(specific))
        self.assertTrue(any("Engineering" in x["area"]
                            for x in specific["career_fit_cautions"]))

    def test_treasury_specialism_is_not_generic_budget_management(self):
        general=fitted("Operations Manager")
        treasury=fitted("Treasury Manager")
        self.assertLess(evidence_index(treasury),evidence_index(general))
        self.assertGreater(treasury["career_fit_penalty"],0)

    def test_executive_assistant_and_intern_are_not_top_career_transfers(self):
        manager=fitted("Vendor Relations Manager")
        assistant=fitted("Executive Assistant, Marketing")
        intern=fitted("Events Intern")
        self.assertGreater(evidence_index(manager),evidence_index(assistant))
        self.assertGreater(evidence_index(manager),evidence_index(intern))
        self.assertTrue(intern["career_fit_cautions"])

    def test_specialist_field_evidence_avoids_penalty(self):
        advanced=RESUME+"\\nManaged IT operations, IT management and software development."
        title={"title":"IT Manager","description":GENERIC_DUTIES}
        self.assertEqual(evaluate_career_fit(title,advanced)["penalty"],0)
        self.assertGreater(evaluate_career_fit(title,RESUME)["penalty"],0)

    def test_new_graduate_is_not_penalized_for_entry_job(self):
        title={"title":"Administrative Assistant","description":GENERIC_DUTIES}
        self.assertEqual(evaluate_career_fit(
            title,"Two years providing customer support.")["penalty"],0)

    def test_operations_and_vendor_roles_remain_fair_cross_industry_matches(self):
        for title in ["Vendor Relations Manager",
                      "Operations Manager - Healthcare Services",
                      "Partnerships Manager", "Customer Success Manager"]:
            with self.subTest(title=title):
                self.assertEqual(evaluate_career_fit(
                    {"title":title,"description":GENERIC_DUTIES},RESUME)["penalty"],0)

    def test_cautions_export_without_false_disqualification(self):
        q=fitted("Capital Markets Analyst")
        self.assertTrue(q["career_fit_cautions"])
        row=breakdowns_csv_rows([{
            "title":"Capital Markets Analyst","company":"Example",
            "qualification_match":q
        }])[0]
        self.assertIn("Specialist accounting",row["Additional career-fit cautions"])
        self.assertGreater(row["Career-fit ranking caution (points)"],0)
        self.assertNotIn("unqualified",row["Additional career-fit cautions"].lower())


if __name__=="__main__":
    unittest.main()
