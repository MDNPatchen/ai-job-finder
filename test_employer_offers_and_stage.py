"""Regression suite for v3.1.4 offer/benefit false positives and role-stage sorting.

These are synthetic applicant/vacancy examples, not actual employer listings.
"""
import unittest

from posting_requirements import extract_posting_requirements
from career_fit_guardrails import evaluate_career_fit
from qualification_matcher import assess_job_qualifications, compile_resume_profile
from ranked_breakdowns import breakdowns_csv_rows,evidence_index

SENIOR_RESUME=(
    "Group newspaper publisher and operations director with 25 years of "
    "regional multi-site operations, team leadership, budgeting, P&L, "
    "advertising sales, marketing strategy, vendor contracts and "
    "community partnership development. "
)
EARLY_RESUME="Customer service associate with two years of front-line experience."
LEADERSHIP_DUTIES=(
    "Own budgets, supervise teams, improve multi-location business operations, "
    "build partnerships, negotiate contracts, lead managers, plan regional strategy "
    "and support revenue growth. "*7
)


def qualify(title,description,resume=SENIOR_RESUME):
    job={"title":title,"description":description}
    return assess_job_qualifications(job,compile_resume_profile(resume,()),resume)


def evaluate(title,description,resume=SENIOR_RESUME):
    return extract_posting_requirements(
        {"title":title,"description":description},resume)


class EmployerOfferVsQualificationTests(unittest.TestCase):
    def test_clear_ops_vp_holistic_rewards_ignored(self):
        desc=(
            "<h3>What You'll Do</h3><p>"+LEADERSHIP_DUTIES+"</p>"
            "<h3>What You're Great At</h3>"
            "<p>Operations leadership, program execution and communication.</p>"
            "<p>We offer holistic total rewards, including comprehensive "
            "healthcare plans, family-building benefits (fertility and "
            "adoption/surrogacy support), flexible time off, annual wellness "
            "and equity packages.</p>"
        )
        result=evaluate("Vice President, Operations - South",desc)
        self.assertFalse(any(x["area"]=="Compensation and equity administration"
                             for x in result["checks"]))
        q=qualify("Vice President, Operations - South",desc)
        self.assertEqual(q["posting_requirement_penalty"],0)
        self.assertGreater(evidence_index(q),65)

    def test_imprint_gm_compensation_equity_packages_not_required(self):
        desc=(
            "<h2>What you'll need</h2><li>Lead teams, drive revenues, "
            "negotiate vendor partnerships.</li>"
            "<h2>What we offer</h2><li>Competitive compensation and "
            "equity packages</li><li>Paid time off and health benefits</li>"
        )
        q=qualify("General Manager - New York City",desc)
        self.assertEqual(q["posting_requirement_penalty"],0)
        self.assertFalse(any(c["area"]=="Compensation and equity administration"
                             for c in q["posting_requirement_checks"]))

    def test_human_readable_imprint_line_without_heading_is_not_required(self):
        desc="What you'll need\nStrong leadership experience\n- Competitive compensation and equity packages"
        x=evaluate("General Manager",desc)
        self.assertFalse(any(v["ranking_caution"] for v in x["checks"]))

    def test_explicit_total_rewards_manager_must_still_be_penalized(self):
        desc=(
            "<h3>What You Need</h3>"
            "<li>7+ years managing total rewards programs, compensation "
            "benchmarking and equity compensation administration.</li>"
        )
        q=qualify("Manager, Compensation & Equity",desc)
        self.assertTrue(any(x["area"]=="Compensation and equity administration"
                            and x["ranking_caution"]>0
                            for x in q["posting_requirement_checks"]))
        self.assertTrue(any(c["ranking_caution"]>0
                            for c in q["career_fit_cautions"]))
        self.assertGreater(q["posting_requirement_penalty"],0)
        self.assertGreater(q["ranking_overlap_relief"],0)

    def test_real_compensation_experience_keeps_specialist_penalty_zero(self):
        desc="<h2>Qualifications</h2><li>7 years of equity compensation administration experience.</li>"
        resume=(SENIOR_RESUME+
                "Managed equity compensation administration for seven years.")
        q=qualify("Manager, Compensation & Equity",desc,resume)
        self.assertEqual(q["posting_requirement_penalty"],0)

    def test_other_specializations_cannot_be_false_requirements_in_benefits(self):
        desc=(
            "<h2>Qualifications</h2><li>Multi-site operations leadership.</li>"
            "<h2>Benefits</h2><li>Healthcare coverage, professional design "
            "training, and employee wellness including OSHA safety courses.</li>"
        )
        report=evaluate("Regional Operations Manager",desc)
        self.assertFalse(any(v["ranking_caution"] for v in report["checks"]))

    def test_compensation_offers_not_exported_as_mandatory(self):
        desc="<h2>What We Offer</h2><li>Competitive compensation and equity packages</li>"
        q=qualify("General Manager",desc)
        job={"title":"General Manager","company":"Example Co","qualification_match":q}
        row=breakdowns_csv_rows([job])[0]
        self.assertNotIn("Compensation and equity administration",
                         row["Employer minimum requirements to verify"])
        self.assertEqual(row["Employer-specific ranking cautions (points)"],0)


class SeniorCareerStageTests(unittest.TestCase):
    def test_sourcing_specialist_below_cross_industry_operations_manager(self):
        a=qualify("Regional Operations Manager",LEADERSHIP_DUTIES)
        b=qualify("Sourcing Specialist",LEADERSHIP_DUTIES)
        self.assertGreater(evidence_index(a),evidence_index(b))
        self.assertGreater(b["career_fit_penalty"],0)

    def test_talent_coordinator_not_equal_to_department_leadership(self):
        for title in ("Talent Acquisition Coordinator","Recruiting Coordinator",
                      "Purchasing Coordinator","Marketing Coordinator"):
            with self.subTest(title=title):
                self.assertGreater(
                    evaluate_career_fit({"title":title},SENIOR_RESUME)["penalty"],0)

    def test_store_assistant_manager_lower_than_area_manager(self):
        area=qualify("Regional Operations Manager",LEADERSHIP_DUTIES)
        assistant=qualify("Assistant Store Manager",LEADERSHIP_DUTIES)
        self.assertGreater(evidence_index(area),evidence_index(assistant))
        self.assertGreater(assistant["career_fit_penalty"],0)

    def test_genuine_procurement_manager_keeps_cross_industry_ranking(self):
        for title in ("Procurement Manager","Vendor Relations Director",
                      "Operations Manager - Healthcare Services",
                      "Partnership Director","Supply Chain Manager"):
            with self.subTest(title=title):
                self.assertEqual(evaluate_career_fit(
                    {"title":title,"description":LEADERSHIP_DUTIES},
                    SENIOR_RESUME)["penalty"],0)

    def test_early_career_resume_has_no_senior_stage_penalty(self):
        self.assertEqual(evaluate_career_fit(
            {"title":"Sourcing Specialist"},EARLY_RESUME)["penalty"],0)

    def test_transfer_only_and_specialist_requirement_regressions(self):
        transfer=qualify("Accounting Coordinator (TRANSFER ONLY)",LEADERSHIP_DUTIES)
        self.assertTrue(transfer["application_restricted"])
        self.assertGreater(transfer["posting_requirement_penalty"],0)
        cases=[
            ("EHS Specialist","5 years experience managing OSHA compliance and "
             "environmental health and safety (EHS) programs."),
            ("Manager, Product Design","8 years of product design and UX design experience."),
            ("Senior Scientist Mass Spec Production","4 years LC-MS/MS mass spectrometry "
             "laboratory experience."),
        ]
        for title,req in cases:
            with self.subTest(title=title):
                q=qualify(title,"<h2>What You Need</h2><li>"+req+"</li>")
                self.assertGreater(q["posting_requirement_penalty"],0)


if __name__=="__main__":
    unittest.main()
