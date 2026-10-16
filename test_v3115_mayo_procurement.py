"""Regression tests from the 2026-10-16 ranked v3.1.14 CSV.

Mayo role titles were replaced by the generic site slogan "Breakthrough";
an actual manufacturing-purchasing minimum was not evaluated at all.
"""
import unittest

from mayo_source import fetch_mayo_jobs, parse_detail
from posting_requirements import extract_posting_requirements
from qualification_matcher import assess_job_qualifications, compile_resume_profile
from ranked_breakdowns import breakdowns_csv_rows


MAYO_DELIVERY="https://jobs.mayoclinic.org/job/rochester/delivery-manager/33647/101908842912"
MAYO_SECURITY="https://jobs.mayoclinic.org/job/rochester/manager-information-security/33647/101621298800"
DETAIL=(
    '<h1>Breakthrough</h1><p>Mayo Clinic'
    'Date posted 10/14/2026 Rochester, Minnesota</p>'
    '<h2>Job description</h2><p>Lead a management team.</p>'
)
PURCHASING=(
    "<h2>Position Summary</h2>"
    "<li>Supervise the end-to-end purchasing process and vendor contracts.</li>"
    "<li>Supervise and ensure department metrics and KPIs.</li>"
    "<h2>Qualifications</h2>"
    "<li>Bachelor's degree in business, supply chain, or operations management "
    "required, or equivalent combination of education and experience.</li>"
    "<li>At least 3 years of purchasing or buying experience in a "
    "manufacturing environment.</li>"
    "<li>Strong written and verbal communication.</li>"
)
RESUME=(
    "Group Newspaper Publisher. 25 years P&L, budgeting, staff leadership, "
    "multiple sites, newspaper circulation distribution, supplier and "
    "vendor contract negotiations. Bachelor's degree in Business Management."
)
MANUFACTURING_RESUME=(
    RESUME+" Five years of manufacturing purchasing experience, "
    "including industrial procurement and buyer management."
)


class MayoTitleRegression(unittest.TestCase):
    def test_delivery_manager_ignores_generic_breakthrough_heading(self):
        job=parse_detail(DETAIL,MAYO_DELIVERY)
        self.assertEqual(job['title'],'Delivery Manager')
        self.assertEqual(job['url'],MAYO_DELIVERY)

    def test_information_security_manager_not_breakthrough(self):
        job=parse_detail(DETAIL,MAYO_SECURITY)
        self.assertEqual(job['title'],'Manager Information Security')
        self.assertEqual(job['url'],MAYO_SECURITY)

    def test_real_role_heading_wins_over_generic_marketing_header(self):
        detail=DETAIL.replace(
            '<p>Mayo Clinic',
            '<h1>Manager, Information Security</h1><p>Mayo Clinic')
        self.assertEqual(parse_detail(detail,MAYO_SECURITY)['title'],
                         'Manager, Information Security')

    def test_search_anchor_used_if_clean_and_specific(self):
        self.assertEqual(parse_detail(DETAIL,MAYO_SECURITY,
                                     "Manager - Information Security")['title'],
                         'Manager - Information Security')

    def test_noisy_search_anchor_does_not_include_location(self):
        job=parse_detail(DETAIL,MAYO_DELIVERY,
                         "Delivery Manager Rochester, Minnesota")
        self.assertEqual(job['title'],'Delivery Manager')

    def test_fetch_jobs_maps_search_titles_to_correct_detail(self):
        search=(
            '<a href="/job/rochester/delivery-manager/33647/101908842912">'
            '<h2>Delivery Manager</h2></a>'
            '<a href="/job/rochester/manager-information-security/33647/101621298800">'
            '<h2>Manager - Information Security</h2></a>'
        )
        def fake(url):
            return search if "/search-jobs?" in url else DETAIL
        results=fetch_mayo_jobs(fake)
        by_url={v["url"]:v["title"] for v in results}
        self.assertEqual(by_url[MAYO_DELIVERY],"Delivery Manager")
        self.assertEqual(by_url[MAYO_SECURITY],"Manager - Information Security")
        self.assertNotIn("Breakthrough",set(by_url.values()))


class ManufacturingProcurementRequirements(unittest.TestCase):
    @staticmethod
    def req(text=PURCHASING,resume=RESUME,title="Purchasing Supervisor"):
        return extract_posting_requirements({
            "title":title,"description":text},resume)

    def test_three_years_manufacturing_buying_requires_specialist_evidence(self):
        r=self.req()
        item=next(x for x in r["checks"] if
             x["area"]=="Manufacturing purchasing / buying experience")
        self.assertEqual(item["ranking_caution"],24,item)
        self.assertTrue(item["priority"].startswith("Required"),item)
        self.assertIn("manufacturing environment",item["listing_excerpt"])
        self.assertIn("No matching field",item["resume_status"])

    def test_vendor_and_supply_contracts_alone_do_not_satisfy_requirement(self):
        r=self.req(resume=RESUME+" Managed printing vendors and newspaper suppliers.")
        self.assertEqual(r["ranking_caution"],24,r)

    def test_documented_manufacturing_purchasing_experience_meets_field_check(self):
        r=self.req(resume=MANUFACTURING_RESUME)
        item=next(x for x in r["checks"] if
             x["area"]=="Manufacturing purchasing / buying experience")
        self.assertEqual(item["ranking_caution"],0,item)

    def test_career_scoring_and_export_retain_specialist_caution(self):
        job={"title":"Purchasing Supervisor","description":PURCHASING,
             "company":"Industrial Electric Manufacturing",
             "url":"https://job-boards.greenhouse.io/industrialelectricmanufacturing/jobs/4409876009",
             "source":"Greenhouse"}
        scored=assess_job_qualifications(
            job,compile_resume_profile(RESUME,()),RESUME)
        checks=scored['posting_requirement_checks']
        self.assertTrue(any(x['area']=="Manufacturing purchasing / buying experience"
                            and x['ranking_caution']==24
                            and x['applied_ranking_caution']==24
                            for x in checks),checks)
        job['qualification_match']=scored
        csv=breakdowns_csv_rows([job])[0]
        self.assertIn('Manufacturing purchasing / buying experience',
                      csv['Employer minimum requirements to verify'])
        self.assertGreaterEqual(csv['Employer-specific ranking cautions (points)'],24)

    def test_manufacturing_procurement_is_not_assumed_in_other_sectors(self):
        job=("<h2>Qualifications</h2>"
             "<li>At least 3 years vendor negotiation and general purchasing "
             "experience in publishing companies.</li>")
        self.assertFalse(any(x["area"]=="Manufacturing purchasing / buying experience"
                             for x in self.req(job)['checks']))

    def test_preferred_manufacturing_procurement_is_not_mandatory(self):
        job=("<h2>Preferred Qualifications</h2>"
             "<li>Manufacturing purchasing experience preferred.</li>")
        r=self.req(job)
        self.assertFalse(any(x["area"]=="Manufacturing purchasing / buying experience"
                             and x["ranking_caution"]>0 for x in r["checks"]))

    def test_manufacturing_keyword_in_role_responsibility_no_penalty(self):
        job=("<h2>Responsibilities</h2>"
             "<li>Oversee suppliers serving manufacturing customers.</li>")
        self.assertEqual(self.req(job)["ranking_caution"],0)


if __name__ == "__main__":
    unittest.main()
