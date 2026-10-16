"""Version 3.1.13 checks from the actual v3.1.12 ranked CSV.

The snippets reproduce relevant exported employer language. These tests
do not assert that positions are still accepting applications or that an
applicant is formally qualified.
"""
import unittest
from posting_requirements import extract_posting_requirements
from formal_qualification_guardrails import extract_formal_minimums
from qualification_matcher import compile_resume_profile,assess_job_qualifications
from ranked_breakdowns import breakdowns_csv_rows

RESUME=(
    "Regional group newspaper publisher and operations director. "
    "Managed department heads, multi-site businesses, sales, P&L, "
    "strategic planning, employee teams, distribution, vendors and "
    "contracts. Bachelor's degree in Business Administration."
)
DUTIES=("Lead operations, budgets, staff, vendors, multi-site contracts, "
        "projects, departmental managers and strategy. "*6)


def posting(title,desc,resume=RESUME):
    return extract_posting_requirements({"title":title,"description":desc},resume)


def formal(title,desc,resume=RESUME):
    return extract_formal_minimums({"title":title,"description":desc},resume)


def scored(title,desc,resume=RESUME):
    return assess_job_qualifications({"title":title,"description":desc},
        compile_resume_profile(resume,()),resume)


def construction_item(report):
    return next((x for x in report["checks"]
        if x["area"]=="Construction / preconstruction delivery experience"),None)


def bachelor_item(report):
    return next((x for x in report["checks"]
        if x["area"].startswith("Bachelor degree")),None)


class ConstructionWorkYearsTests(unittest.TestCase):
    def test_red_bull_years_of_work_without_word_experience(self):
        clause="5+ years of work in Construction Project Management or related fields"
        q=posting("Project Manager - Real Estate, Construction, and Building Operations",
                  "<h2>Qualifications</h2><li>"+clause+"</li>"+DUTIES)
        item=construction_item(q)
        self.assertIsNotNone(item)
        self.assertGreater(item["ranking_caution"],0,item)
        self.assertTrue(item["priority"].startswith("Required"),item)

    def test_sb_usa_ten_years_in_preconstruction_no_experience_word(self):
        q=posting("Vice President, Estimating",
            "<h2>Required Qualifications</h2><li>10+ years in preconstruction</li>"+DUTIES)
        item=construction_item(q)
        self.assertIsNotNone(item)
        self.assertGreater(item["ranking_caution"],0,item)

    def test_standalone_ten_years_field_minimum_without_heading(self):
        item=construction_item(posting("Vice President, Estimating",
            "10+ years in preconstruction"))
        self.assertGreater(item["ranking_caution"],0,item)

    def test_arco_required_construction_experience_later_preferred_clause(self):
        clause=("2-5 years of construction management and/or estimating "
                "experience required, previous design/build project "
                "experience strongly preferred")
        for title in ("Project Manager, Mission Critical Construction",
                      "Project Manager, Mission Critical Construction - TX"):
            with self.subTest(title=title):
                q=posting(title,"<h2>Qualifications</h2><li>"+clause+"</li>")
                item=construction_item(q)
                self.assertIsNotNone(item)
                self.assertTrue(item["priority"].startswith("Required"),item)
                self.assertGreater(item["ranking_caution"],0,item)

    def test_actually_preferred_construction_experience_is_not_required(self):
        desc=("<h2>Preferred Qualifications</h2><li>2-5 years of construction "
              "management experience strongly preferred.</li>")
        q=posting("Project Manager",desc)
        item=construction_item(q)
        self.assertTrue(item is None or item["ranking_caution"]==0,item)

    def test_broward_education_only_still_no_experience_penalty(self):
        desc=("Requires a Bachelor's degree from an accredited college "
              "or university with major coursework in architecture, "
              "engineering, construction management, hydrology and "
              "environmental sciences or closely related field")
        item=construction_item(posting("Capital Program Administrator",desc))
        self.assertTrue(item is None or item["ranking_caution"]==0,item)

    def test_lv_equivalent_experience_is_not_separate_minimum(self):
        desc=("<h2>Qualifications</h2><li>Bachelor's degree in "
              "Construction Management, Engineering, Architecture, "
              "or related field or equivalent experience.</li>")
        item=construction_item(posting("Construction Project Manager",desc))
        self.assertTrue(item is None or item["ranking_caution"]==0,item)

    def test_dexterra_degree_and_equivalent_work_does_not_double_charge(self):
        desc=("<h2>Qualifications</h2><li>Bachelor's degree in "
              "construction management, engineering, business, or "
              "equivalent combination of education and work experience.</li>")
        item=construction_item(posting("Facility Project Manager",desc))
        self.assertTrue(item is None or item["ranking_caution"]==0,item)

    def test_actual_degree_plus_separate_work_requirement_both_apply(self):
        desc=("<h2>Qualifications</h2>"
              "<li>Bachelor's degree in construction management required.</li>"
              "<li>Minimum eight years of construction project management "
              "experience is required.</li>"+DUTIES)
        q=scored("Senior Construction Project Manager",desc)
        checks=q["posting_requirement_checks"]
        self.assertTrue(any(x["type"]=="Education / professional credential"
                            and x["applied_ranking_caution"]>0
                            for x in checks))
        self.assertTrue(any(x["area"]=="Construction / preconstruction delivery experience"
                            and x["applied_ranking_caution"]>0
                            for x in checks))

    def test_duration_in_project_team_bio_not_independent_requirement(self):
        desc=("<h2>Responsibilities</h2>"
              "<li>Work with our construction team, serving clients for "
              "more than 20 years.</li>"+DUTIES)
        item=construction_item(posting("Operations Director",desc))
        self.assertTrue(item is None or item["ranking_caution"]==0,item)


class DegreeRequirementTests(unittest.TestCase):
    def test_broward_requires_bachelors_before_degree_term(self):
        desc=("Requires a Bachelor's degree from an accredited college or "
              "university with major coursework in architecture, engineering, "
              "construction management, hydrology and environmental sciences "
              "or closely related field")
        result=formal("Capital Program Administrator (Resilience Engineer)",desc)
        item=bachelor_item(result)
        self.assertIsNotNone(item)
        self.assertTrue(item["priority"].startswith("Required"),item)
        self.assertGreater(item["ranking_caution"],0,item)
        self.assertTrue(result["unverified_mandatory"])
        q=scored("Capital Program Administrator",desc+DUTIES)
        exported=breakdowns_csv_rows([{"title":"Capital Program Administrator",
                                      "company":"Broward County",
                                      "qualification_match":q}])[0]
        self.assertIn("Required",exported["Employer minimum requirements to verify"])

    def test_explicit_must_have_bachelor_degree(self):
        desc="<h2>Qualifications</h2><li>Must have a Bachelor's degree in Engineering.</li>"
        item=bachelor_item(formal("Project Executive",desc))
        self.assertIsNotNone(item)
        self.assertGreater(item["ranking_caution"],0,item)

    def test_preferred_bachelors_still_not_mandatory(self):
        desc="<h2>Preferred Qualifications</h2><li>Bachelor's degree in Engineering is preferred.</li>"
        result=formal("Project Manager",desc)
        self.assertEqual(result["ranking_caution"],0)
        self.assertFalse(result["unverified_mandatory"])

    def test_equivalent_experience_alternative_still_nonmandatory(self):
        desc=("<h2>Qualifications</h2><li>Requires a Bachelor's degree in "
              "Construction Management or equivalent combination of education "
              "and relevant work experience.</li>")
        result=formal("Construction Manager",desc)
        self.assertEqual(result["ranking_caution"],0)
        self.assertFalse(result["unverified_mandatory"])

    def test_mayo_bachelor_or_associate_pathways_still_not_cumulative(self):
        desc=("<h2>Qualifications</h2>"
              "<li>Bachelor's degree in Construction Management required "
              "and 10 years project experience.</li>"
              "<li>Or, an Associate's degree in Construction Management "
              "required and 15 years project experience.</li>")
        q=formal("Project Manager II-Facilities",desc)
        items=[x for x in q["checks"] if x["area"].startswith(("Bachelor","Associate"))]
        self.assertEqual(len(items),2)
        self.assertEqual(sum(x["ranking_caution"] for x in items),22)
        self.assertTrue(all(x.get("alternative_degree_pathways") for x in items))

if __name__=="__main__":
    unittest.main()
