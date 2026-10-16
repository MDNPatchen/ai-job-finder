"""No-network 3.1.12: experience versus education and alternative degrees.

Employer examples are synthetic regressions based on v3.1.11 CSV extracts;
the app still asks users to verify complete minimums with the employer.
"""
import unittest
from posting_requirements import extract_posting_requirements
from formal_qualification_guardrails import extract_formal_minimums
from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index, breakdowns_csv_rows

RESUME=(
    "Group Newspaper Publisher and Regional Operations Director. "
    "25 years of operational management, P&L budgets, employee supervision, "
    "vendor contracts, community partnerships and newspaper distribution. "
    "Bachelor's degree in Business Administration."
)
DUTIES=("Lead program teams, annual budgets, senior staff, strategic "
        "development, supplier contracts and regional operations. "*5)


def posting(title,text,resume=RESUME):
    return extract_posting_requirements(
        {"title":title,"description":text},resume)


def formal(title,text,resume=RESUME):
    return extract_formal_minimums(
        {"title":title,"description":text},resume)


def scored(title,text,resume=RESUME):
    return assess_job_qualifications(
        {"title":title,"description":text},
        compile_resume_profile(resume,()),resume)


def construction_experience_items(report):
    return [x for x in report["checks"]
            if x["area"]=="Construction / preconstruction delivery experience"]


def education_items(report):
    return [x for x in report["checks"]
            if x["type"]=="Education / professional credential"]


class EducationVsExperienceTests(unittest.TestCase):
    def test_broward_coursework_is_not_construction_work_history(self):
        text=("Requires a Bachelor's degree from an accredited college or "
              "university with major coursework in architecture, engineering, "
              "construction management, hydrology, environmental sciences or "
              "closely related field.")
        p=posting("Capital Program Administrator (Resilience Engineer)",text)
        self.assertFalse(any(x["ranking_caution"]>0
                             for x in construction_experience_items(p)))
        self.assertFalse(any(x["ranking_caution"]>0
                             for x in education_items(p)))  # different subsystem
        # Professional education remains visible to the formal checker.
        f=formal("Capital Program Administrator",text)
        self.assertTrue(education_items(f))

    def test_dexterra_degree_or_equivalent_experience_no_second_penalty(self):
        text=("<h2>Qualifications</h2><li>Bachelor's degree in facilities "
              "management, engineering, construction management, business "
              "administration, or related field required; an equivalent "
              "combination of relevant education and progressively responsible "
              "experience may be considered.</li>")
        p=posting("Facility Project Manager",text)
        self.assertEqual(sum(x["ranking_caution"]
                             for x in construction_experience_items(p)),0)
        self.assertEqual(formal("Facility Project Manager",text)
                         ["ranking_caution"],0)

    def test_lv_degree_or_equivalent_experience_without_years(self):
        text=("<h2>Qualifications</h2><li>Bachelor's degree in Construction "
              "Management, Civil Engineering, Architecture, or related field "
              "(or equivalent experience)</li>")
        p=posting("Construction Project Manager",text)
        self.assertEqual(sum(x["ranking_caution"]
                             for x in construction_experience_items(p)),0)
        self.assertEqual(formal("Construction Project Manager",text)
                         ["ranking_caution"],0)

    def test_preferred_construction_degree_does_not_set_experience_minimum(self):
        text=("<h2>Nice to Have</h2><li>Bachelor's degree in construction "
              "management preferred.</li>")
        p=posting("Project Manager",text)
        self.assertEqual(sum(x["ranking_caution"]
                             for x in construction_experience_items(p)),0)

    def test_true_independent_experience_in_separate_bullet_stays_penalized(self):
        text=("<h2>Qualifications</h2><li>Bachelor's degree in Construction "
              "Management, Engineering or Architecture is required.</li>"
              "<li>Minimum eight years of experience managing commercial "
              "construction projects required.</li>"+DUTIES)
        p=posting("Senior Construction Project Manager",text)
        self.assertTrue(any(x["ranking_caution"]>=25
                            for x in construction_experience_items(p)))
        self.assertGreaterEqual(formal("Senior Construction Project Manager",text)
                                ["ranking_caution"],22)
        q=scored("Senior Construction Project Manager",text)
        self.assertTrue(any(x["type"]=="Field-specific experience"
                            and x["applied_ranking_caution"]>0
                            for x in q["posting_requirement_checks"]))
        self.assertTrue(any(x["type"]=="Education / professional credential"
                            and x["applied_ranking_caution"]>0
                            for x in q["posting_requirement_checks"]))

    def test_years_and_degree_in_same_bullet_preserve_independent_work(self):
        text=("<h2>Qualifications</h2><li>Bachelor's degree in construction "
              "management and 10 years of experience overseeing commercial "
              "construction projects are required.</li>")
        self.assertGreater(posting("Project Manager",text)
                           ["ranking_caution"],0)


class AlternativeEducationPathwayTests(unittest.TestCase):
    def test_mayo_bachelor_or_associate_not_cumulative(self):
        text=("<h2>Qualifications</h2><li>A minimum of a four-year college "
              "degree (Bachelor's degree) in project or construction "
              "management, engineering, architecture or related field, "
              "and a minimum of 10 years' post-academic experience managing "
              "design and construction phases for projects.</li>"
              "<li>Or, an Associate's degree in project or construction "
              "management, engineering, architecture or related field, "
              "and a minimum of 15 years of post-academic professional "
              "construction project management experience.</li>"+DUTIES)
        r=formal("Project Manager II-Facilities",text)
        degrees=[x for x in education_items(r)
                 if x["area"].startswith(("Bachelor","Associate"))]
        self.assertEqual(len(degrees),2,degrees)
        self.assertEqual(sum(x["ranking_caution"] for x in degrees),22,degrees)
        self.assertEqual(sum(bool(x["ranking_caution"]) for x in degrees),1)
        self.assertTrue(all(x.get("alternative_degree_pathways") for x in degrees))
        self.assertTrue(all("alternative degree route" in x["priority"]
                            for x in degrees))
        self.assertTrue(r["unverified_mandatory"])
        q=scored("Project Manager II-Facilities",text)
        csv=breakdowns_csv_rows([{"title":"Project Manager II-Facilities",
                                 "company":"Example Clinic",
                                 "qualification_match":q}])[0]
        self.assertIn("alternative degree route",csv["Employer minimum requirements to verify"])
        self.assertLess(evidence_index(q),90)

    def test_documented_technical_bachelor_satisfies_one_route(self):
        text=("<h2>Qualifications</h2>"
              "<li>Bachelor's degree in Construction Management is required.</li>"
              "<li>Or, an Associate's degree in construction management "
              "is required with additional experience.</li>")
        technical=RESUME+" Earned a Bachelor's degree in Construction Management."
        r=formal("Project Manager",text,technical)
        self.assertEqual(r["ranking_caution"],0)
        self.assertFalse(r["unverified_mandatory"])

    def test_independent_bachelor_required_master_preferred_not_grouped(self):
        text=("<h2>Qualifications</h2><li>Bachelor's degree in "
              "Engineering required.</li><li>Master's degree preferred.</li>")
        r=formal("Construction Director",text)
        self.assertGreater(r["ranking_caution"],0)
        self.assertFalse(any(x.get("alternative_degree_pathways")
                             for x in education_items(r)))

    def test_required_two_degrees_not_joined_without_or(self):
        text=("<h2>Qualifications</h2><li>Master's degree in business "
              "is required.</li><li>Bachelor's degree in engineering "
              "is required.</li>")
        r=formal("Research Director",text)
        self.assertGreaterEqual(r["ranking_caution"],22)
        self.assertFalse(any(x.get("alternative_degree_pathways")
                             for x in education_items(r)))


if __name__=="__main__":
    unittest.main()
