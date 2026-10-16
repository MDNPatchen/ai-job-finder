"""Regression tests for 3.1.6: equity grants, abbreviated internal restrictions,
specialist industry years, and career level.

All postings and résumés below are synthetic, based on error patterns observed
in ranked exports. No hiring eligibility judgment is made.
"""
import unittest

from posting_requirements import extract_posting_requirements
from qualification_matcher import assess_job_qualifications,compile_resume_profile
from career_fit_guardrails import evaluate_career_fit
from ranked_breakdowns import breakdowns_csv_rows,evidence_index

RESUME=(
    "Group newspaper publisher and operations director with 25 years of "
    "regional multi-site business leadership. Managed department heads, "
    "annual budgets, full P&L, vendor contracts, print distribution and "
    "logistics. Led advertising revenue, marketing, community partnerships "
    "and operational transformation."
)
DUTIES=(
    "Lead strategic planning, multi-site operations and cross-functional "
    "teams, negotiate contracts, oversee budgets, optimize distribution, "
    "develop partnerships and deliver revenue growth. "*7
)
GRANT=(
    "Additionally, this role will be eligible for refresh equity grants "
    "as part of our ongoing compensation program."
)


def check(title, description, resume=RESUME):
    return extract_posting_requirements(
        {"title":title,"description":description},resume)


def score(title, description=DUTIES, resume=RESUME):
    return assess_job_qualifications(
        {"title":title,"description":description},
        compile_resume_profile(resume,()),resume)


class GrantAndInternalAccessTests(unittest.TestCase):
    def test_clear_refresh_grants_in_misplaced_applicant_section(self):
        for title in (
            "Lead Product Manager, Mobile",
            "Director, Payments Performance - Product",
            "Customer Success Director - Healthcare (C1 - B2B)",
            "Senior Manager Customer Success - Healthcare (C1 - B2B)",
        ):
            with self.subTest(title=title):
                text=(
                    "<h2>What You're Great At</h2><li>Experience in "
                    "leadership and managing enterprise programs.</li><li>"
                    +GRANT+"</li>"
                )
                details=check(title,text)
                self.assertFalse(any(
                    x["area"]=="Compensation and equity administration"
                    for x in details["checks"]), details["checks"])
                self.assertEqual(details["ranking_caution"],0)

    def test_equity_eligibility_without_section_heading(self):
        text=GRANT+" The compensation program also covers health insurance."
        self.assertEqual(check("General Manager",text)["ranking_caution"],0)

    def test_receiving_equity_vs_administering_others_equity(self):
        text="<h2>Qualifications</h2><li>Seven years of experience administering equity compensation and stock award plans for employees.</li>"
        q=check("Manager, Compensation & Equity",text)
        self.assertGreater(q["ranking_caution"],0)
        self.assertTrue(any(x["area"]=="Compensation and equity administration"
                            for x in q["checks"]))

    def test_hennepin_abbreviated_internal_restriction(self):
        title="Classification Analyst (Internal HC applicants only)"
        q=score(title,DUTIES)
        self.assertTrue(q["application_restricted"])
        self.assertGreaterEqual(q["posting_requirement_penalty"],45)
        exported=breakdowns_csv_rows([{
            "title":title,"company":"Hennepin County",
            "qualification_match":q}])[0]
        self.assertEqual(exported["Posting explicitly restricts to internal applicants"],
                         "Yes — verify eligibility")
        self.assertIn("Internal applicants only",exported["Employer minimum requirements to verify"])

    def test_internal_specific_employer_abbreviation_variations(self):
        for title in (
            "Classification Analyst (Internal HC applicants only)",
            "Analyst — internal ABC candidates only",
            "Operations Manager (internal County employees only)",
        ):
            with self.subTest(title=title):
                self.assertTrue(check(title,DUTIES)["application_restricted"])

    def test_not_false_internal_restriction(self):
        for title,desc in (
            ("Customer Relations Manager","Work with internal HC applicants only when processing forms."),
            ("Regional Manager","This role is open to both internal and external applicants."),
            ("IT Analyst","File transfers only; no external links."),
        ):
            with self.subTest(title=title):
                self.assertFalse(check(title,desc)["application_restricted"])


class SpecialistAndCareerLevelTests(unittest.TestCase):
    def test_social_media_years_are_specific_experience(self):
        text=(
            "<h2>What You'll Need</h2>"
            "<li>5-8 years of experience managing social media campaigns, "
            "paid social and social content strategy across platforms.</li>"
            "<h2>Nice to Have</h2><li>Experience with event logistics preferred.</li>"
        )
        q=score("Senior Social Media Manager",text)
        self.assertTrue(any(x["area"]=="Dedicated social media campaign leadership"
                            and x["ranking_caution"]>0
                            for x in q["posting_requirement_checks"]))
        self.assertTrue(any(x["ranking_caution"]>0 for x in q["career_fit_cautions"]))
        self.assertGreater(q["posting_requirement_penalty"],0)
        self.assertGreater(q["ranking_overlap_relief"],0)
        self.assertLess(evidence_index(q),evidence_index(
            score("Director of Community Partnerships",DUTIES)))

    def test_music_licensing_five_years_are_specialized(self):
        text=(
            "<h2>Qualifications</h2>"
            "<li>5+ years of music licensing, music copyright "
            "clearances, and music publishing rights experience.</li>"
        )
        q=score("Manager, Music Rights & Clearances",text)
        self.assertTrue(any(x["area"]=="Music licensing / copyright clearances"
                            and x["ranking_caution"]>0
                            for x in q["posting_requirement_checks"]))
        self.assertTrue(any(x["ranking_caution"]>0
                            for x in q["career_fit_cautions"]))
        self.assertGreater(q["ranking_overlap_relief"],0)

    def test_duties_mention_does_not_invent_music_license_requirements(self):
        text=(
            "<h2>Responsibilities</h2>"
            "<li>Work with a music licensing vendor and support the "
            "community events program.</li>"
            "<h2>What You'll Need</h2>"
            "<li>Business operations, budgeting and partnerships.</li>"
        )
        result=check("Regional Operations Manager",text)
        self.assertFalse(any(x["area"]=="Music licensing / copyright clearances"
                             and x["ranking_caution"]>0 for x in result["checks"]))

    def test_title_specialist_caution_when_feed_lacks_requirements(self):
        for title in ("Senior Social Media Manager",
                      "Manager, Music Rights & Clearances"):
            with self.subTest(title=title):
                self.assertGreater(
                    evaluate_career_fit({"title":title},RESUME)["penalty"],0)

    def test_event_marketing_requires_specific_evidence(self):
        q=evaluate_career_fit(
            {"title":"Director, Community & Event Marketing"},RESUME)
        self.assertGreater(q["penalty"],0)
        evidence=RESUME+" Led event marketing and annual community event production."
        self.assertEqual(evaluate_career_fit(
            {"title":"Director, Community & Event Marketing"},evidence)["penalty"],0)

    def test_admin_specialist_and_logistics_coordinator_career_level(self):
        for title in ("Administrative Specialist 2 (Finance)",
                      "Logistics Coordinator","Inventory Coordinator"):
            with self.subTest(title=title):
                self.assertGreater(evaluate_career_fit(
                    {"title":title},RESUME)["penalty"],0)
                self.assertEqual(evaluate_career_fit(
                    {"title":title},"Two years customer support.")["penalty"],0)
                self.assertLess(evidence_index(score(title,DUTIES)),
                                evidence_index(score("Regional Operations Manager",DUTIES)))

    def test_cross_industry_business_leadership_still_eligible(self):
        for title in (
            "Procurement Manager","Operations Manager - Healthcare Services",
            "Partnership Director","Director of Marketing",
            "Distribution Operations Director",
            "Manager, Music Partnerships",   # partnerships != licensing
        ):
            with self.subTest(title=title):
                self.assertEqual(evaluate_career_fit(
                    {"title":title},RESUME)["penalty"],0)

    def test_domain_resume_evidence_removes_title_penalty(self):
        specialized=RESUME+(
            " Managed social media marketing campaigns and paid social "
            "advertising for seven years. Directed music licensing and "
            "copyright clearances for broadcast programs."
        )
        for title in ("Senior Social Media Manager",
                      "Manager, Music Rights & Clearances"):
            with self.subTest(title=title):
                self.assertEqual(evaluate_career_fit(
                    {"title":title},specialized)["penalty"],0)


if __name__=="__main__":
    unittest.main()
