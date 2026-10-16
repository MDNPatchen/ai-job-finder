"""Offline regressions for 3.1.7 qualification specificity, relocation and degrees.

Descriptions are synthetic approximations of ranking errors, not evidence
that a specific vacancy remains open or that the résumé is unqualified.
"""
import unittest
from formal_qualification_guardrails import extract_formal_minimums
from posting_requirements import extract_posting_requirements
from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index, breakdowns_csv_rows

RESUME=(
    "Group newspaper publisher and operations director with 25 years "
    "leading regional businesses. Managed multiple sites, departmental "
    "managers, annual operating budgets, P&L, contracts, vendors, marketing, "
    "distribution, community events and strategic operations."
)
RELATED_BACHELOR=RESUME+" Earned Bachelor of Science degree in Business Administration."
RELATED_MASTER=RESUME+" Earned Master's degree in Business Administration."
ENGINEERING_RESUME=RESUME+" Earned Bachelor of Science degree in Civil Engineering."
DUTIES=(
    "Lead multi-site operations, staff, annual budgets, program development, "
    "contract negotiations and major vendor relationships. "*7
)


def req(title,desc,resume=RESUME):
    return extract_posting_requirements({"title":title,"description":desc},resume)


def formal(title,desc,resume=RESUME):
    return extract_formal_minimums({"title":title,"description":desc},resume)


def score(title,desc,resume=RESUME):
    job={"title":title,"description":desc}
    return assess_job_qualifications(job,compile_resume_profile(resume,()),resume)


class ExperienceSpecificityTests(unittest.TestCase):
    def test_seo_and_social_familiarity_is_not_campaign_management(self):
        snippets=(
            "<h2>Qualifications</h2><li>Familiarity with SEO and social media.</li>",
            "<h2>What You'll Need</h2><li>Working knowledge of SEO and social media trends.</li>",
            "<h2>What You're Great At</h2><li>Knowledge of TV testing, SEO and social media.</li>",
            "<h2>Qualifications</h2><li>Experience with digital editorial operations and familiarity with social platforms.</li>",
        )
        for text in snippets:
            with self.subTest(text=text):
                q=req("Head of TV Testing, Tom's Guide",text)
                self.assertFalse(any(
                    c["area"]=="Dedicated social media campaign leadership"
                    and c["ranking_caution"]>0 for c in q["checks"]))

    def test_social_campaign_years_still_required(self):
        desc=("<h2>What You'll Need</h2><li>5-8 years of experience managing "
              "social media campaigns, paid social advertising and social content strategy.</li>")
        q=req("Senior Social Media Manager",desc)
        self.assertTrue(any(c["area"]=="Dedicated social media campaign leadership"
                            and c["ranking_caution"]>0 for c in q["checks"]))

    def test_explicit_social_management_without_years(self):
        desc=("<h2>Qualifications</h2><li>Demonstrated social media campaign "
              "management and paid social strategy experience required.</li>")
        self.assertTrue(any(x["area"]=="Dedicated social media campaign leadership"
                            and x["ranking_caution"]>0
                            for x in req("Social Media Manager",desc)["checks"]))

    def test_familiarity_not_reinterpreted_as_requirement_just_because_heading(self):
        desc=("<h2>What You Need</h2><li>Familiarity with social media management "
              "software and SEO; hands-on editorial testing background.</li>")
        q=req("Digital Publishing Director",desc)
        self.assertFalse(any(x["ranking_caution"]>0 for x in q["checks"]))


class ResidencyAlternativeTests(unittest.TestCase):
    def test_hennepin_residency_explicit_relocation_permitted(self):
        desc=("Applicants must reside in Minnesota or Wisconsin or be willing "
              "to relocate to Minnesota or Wisconsin after acceptance. "
              + DUTIES)
        q=req("Operations Manager",desc)
        location=[x for x in q["checks"] if x["type"]=="Residency / location"]
        self.assertTrue(location)
        self.assertEqual(location[0]["ranking_caution"],0)
        self.assertIn("Relocation",location[0]["priority"])

    def test_residence_after_hire_permitted_move(self):
        desc=("City residency is required within six months of hire. "
              "Candidates may relocate to the city to meet this condition. "+DUTIES)
        q=req("Finance Operations Director",desc)
        self.assertTrue(any(x["type"]=="Residency / location" and
                            x["ranking_caution"]==0 for x in q["checks"]))

    def test_strict_residency_without_relocation_still_flagged(self):
        q=req("Operations Manager","Boston residency is required at the time of application.")
        self.assertTrue(any(x["type"]=="Residency / location" and
                            x["ranking_caution"]>0 for x in q["checks"]))

    def test_location_is_not_auto_fulfilled_by_long_career(self):
        q=req("Operations Manager","County residency is required at hire.")
        self.assertTrue(any(x["type"]=="Residency / location" and
                            x["ranking_caution"]>0 for x in q["checks"]))


class MandatoryEducationTests(unittest.TestCase):
    def test_mayo_master_required_not_generic_publisher_experience(self):
        desc=("<h2>Qualifications</h2><li>Master's degree in business, "
              "health care administration or related field and ten years "
              "of operational management experience are required.</li>"+DUTIES)
        f=formal("Senior Director-MCL Operations",desc)
        self.assertTrue(any(x["area"].startswith("Master degree") and
                            x["ranking_caution"]>0 for x in f["checks"]))
        ranked=score("Senior Director-MCL Operations",desc)
        self.assertLess(evidence_index(ranked),90)
        self.assertTrue(any(x["type"]=="Education / professional credential"
                            for x in ranked["posting_requirement_checks"]))
        csv=breakdowns_csv_rows([{
            "title":"Senior Director-MCL Operations","company":"Example Clinic",
            "qualification_match":ranked}])[0]
        self.assertIn("Master degree",csv["Employer minimum requirements to verify"])

    def test_genuine_master_documented_does_not_trigger_penalty(self):
        desc=("<h2>Qualifications</h2><li>Master's degree in business or "
              "health care administration required.</li>"+DUTIES)
        a=formal("Director of Operations",desc,RELATED_MASTER)
        self.assertEqual(a["ranking_caution"],0)
        self.assertFalse(a["unverified_mandatory"])

    def test_brph_architecture_or_engineering_degree(self):
        desc=("<h2>EDUCATION and/or EXPERIENCE:</h2>"
              "<li>Bachelor’s degree in architecture or engineering, from an "
              "accredited four-year college or university.</li>"
              "<li>Ten years leading federal building projects required.</li>"+DUTIES)
        q=formal("Federal Project Executive",desc,RELATED_BACHELOR)
        self.assertGreater(q["ranking_caution"],0)
        self.assertTrue(any("technical" in x["area"] for x in q["checks"]))
        ranked=score("Federal Project Executive",desc,RELATED_BACHELOR)
        self.assertLess(evidence_index(ranked),90)
        e=formal("Federal Project Executive",desc,ENGINEERING_RESUME)
        self.assertEqual(e["ranking_caution"],0)

    def test_bachelor_required_master_preferred_does_not_penalize_master(self):
        desc=("<h2>Qualifications</h2>"
              "<li>Bachelor's degree in Business Administration required, "
              "Master's degree in a related field preferred.</li>"+DUTIES)
        result=formal("Operations Director",desc,RELATED_BACHELOR)
        self.assertFalse(any(x["area"].startswith("Master") and
                             x["ranking_caution"]>0 for x in result["checks"]))
        self.assertEqual(result["ranking_caution"],0)

    def test_alternative_equivalent_experience_does_not_assert_disqualification(self):
        desc=("<h2>Qualifications</h2><li>Bachelor's degree in business, "
              "supply chain management, or equivalent combination of "
              "education and work experience will be considered.</li>"+DUTIES)
        q=formal("Purchasing Supervisor",desc)
        self.assertEqual(q["ranking_caution"],0)
        self.assertFalse(q["unverified_mandatory"])

    def test_degrees_not_penalized_in_employee_benefits(self):
        desc=("<h2>What We Offer</h2><li>Master's degree tuition assistance "
              "and Bachelor's degree education reimbursement.</li>"+DUTIES)
        self.assertEqual(formal("Operations Manager",desc)["ranking_caution"],0)

    def test_professional_architect_license_required_vs_preferred(self):
        mandatory="<h2>Qualifications</h2><li>Must be a licensed architect with current registration.</li>"
        preferred="<h2>Nice to Have</h2><li>Licensed architect highly preferred.</li>"
        self.assertGreater(formal("Federal Project Executive",mandatory)["ranking_caution"],0)
        self.assertEqual(formal("Federal Project Executive",preferred)["ranking_caution"],0)

    def test_executive_role_without_mandatory_degree_can_still_rank_high(self):
        q=formal("Regional Operations Director",DUTIES)
        self.assertFalse(q["checks"])
        self.assertFalse(q["unverified_mandatory"])

if __name__=="__main__":
    unittest.main()
