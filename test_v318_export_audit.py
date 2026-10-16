"""3.1.8: empirical regressions from the 3.1.7 ranked CSV export.

These vacancy snippets are examples, not independent validation of live jobs.
"""
import unittest

from posting_requirements import extract_posting_requirements
from formal_qualification_guardrails import extract_formal_minimums
from qualification_matcher import assess_job_qualifications,compile_resume_profile
from ranked_breakdowns import evidence_index

RESUME=("Group newspaper publisher with 25 years in multi-site operations, "
        "advertising revenue, P&L management, budget forecasts, logistics, "
        "staff supervision, contracts and business partnerships.")


class ExportV318Corrections(unittest.TestCase):
    def test_hennepin_reside_in_or_relocate_to_same_requirement(self):
        desc=("While this position is designated as hybrid, based on current "
              "requirements hires must reside in or relocate to Minnesota "
              "or Wisconsin. The role leads budgets and operational staff.")
        checks=extract_posting_requirements(
            {"title":"Director of Business Operations - Hennepin Health",
             "description":desc},RESUME)["checks"]
        residency=[x for x in checks if x["type"]=="Residency / location"]
        self.assertTrue(residency)
        self.assertEqual(residency[0]["ranking_caution"],0)
        self.assertIn("Relocation",residency[0]["priority"])

    def test_brph_inline_architecture_or_engineering_degree_is_a_minimum(self):
        desc=(
            "Attend project site meetings, design reviews and stakeholder "
            "engagements. EDUCATION and/or EXPERIENCE: "
            "• Bachelor’s degree in architecture or engineering, from an "
            "accredited four-year college or university. "
            "• Ten years of experience as project manager, with preferred "
            "experience on federal construction projects."
        )
        report=extract_formal_minimums(
            {"title":"Federal Project Executive","description":desc},
            RESUME+" Bachelor's degree in Business Administration.")
        bachelor=[x for x in report["checks"] if x["area"].startswith("Bachelor")]
        self.assertTrue(bachelor)
        self.assertTrue(bachelor[0]["priority"].startswith("Required"),bachelor)
        self.assertGreater(bachelor[0]["ranking_caution"],0)

    def test_imprint_senior_social_role_requires_proven_scaling(self):
        desc=(
            "<h2>Qualifications</h2><li>Required - 5–8 years of social media "
            "experience, with a demonstrated track record of building "
            "or significantly scaling social presence for a brand.</li>"
        )
        job={"title":"Senior Social Media Manager","description":desc}
        check=extract_posting_requirements(job,RESUME)
        social=[x for x in check["checks"]
                if x["area"]=="Dedicated social media campaign leadership"]
        self.assertTrue(social)
        self.assertTrue(social[0]["priority"].startswith("Required"),social)
        self.assertGreater(social[0]["ranking_caution"],0)

    def test_editorial_seo_familiarity_not_social_campaign_requirement(self):
        desc=(
            "<h2>Qualifications</h2><li>Familiarity with digital content "
            "distribution including SEO and social media coverage.</li>"
        )
        checks=extract_posting_requirements(
            {"title":"Head of TV Testing, Tom's Guide","description":desc},
            RESUME)
        self.assertFalse(any(x["area"]=="Dedicated social media campaign leadership"
                             and x["ranking_caution"]>0
                             for x in checks["checks"]))

    def test_broad_manager_still_has_no_degree_penalty_without_required_degree(self):
        desc="Oversee budgets, revenue growth, contracts, staff and operations."
        profile=compile_resume_profile(RESUME,())
        report=assess_job_qualifications(
            {"title":"Regional Operations Director","description":desc},
            profile,RESUME)
        self.assertEqual(report["posting_requirement_penalty"],0)
        self.assertGreaterEqual(evidence_index(report),0)


if __name__=="__main__":
    unittest.main()
