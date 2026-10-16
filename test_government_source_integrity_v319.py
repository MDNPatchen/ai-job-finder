"""No-network v3.1.9 source integrity and required-versus-preferred regressions.

Examples based on duplicate URL / wrong-employer records in the v3.1.8
ranked export, with fictitious employer data used only for negative cases.
"""
import ast
import unittest
from pathlib import Path

from government_feed_identity import (
    official_vacancy_agency, belongs_to_configured_agency,
    dedupe_vacancy_urls
)
from formal_qualification_guardrails import extract_formal_minimums
from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index

BOISE_AP="https://www.governmentjobs.com/careers/boiseid/jobs/5504395-0"
BOISE_AR="https://www.governmentjobs.com/careers/boiseid/jobs/5518867-0"
RESUME=("Group publisher and business operations director with 25 years "
        "in business, managing multiple locations, employees, budgets, "
        "vendor contracts, distribution and revenue growth. "
        "Bachelor's degree in Business Administration.")


class GovernmentAgencyAttributionTests(unittest.TestCase):
    def test_official_boise_url_only_belongs_to_boise_not_other_feed(self):
        for url in (BOISE_AP,BOISE_AR):
            self.assertEqual(official_vacancy_agency(url,"NEOGOV"),"boiseid")
            self.assertTrue(belongs_to_configured_agency(url,"boiseid","NEOGOV"))
            for wrong in ("charlottecountyfl","boston","cabq"):
                with self.subTest(wrong=wrong,url=url):
                    self.assertFalse(belongs_to_configured_agency(url,wrong,"NEOGOV"))

    def test_reject_unsupported_or_deceptive_domains(self):
        rejected=(
            "https://www.governmentjobs.com.evil.org/careers/boiseid/jobs/5504395-0",
            "http://www.governmentjobs.com/careers/boiseid/jobs/5504395-0",
            "https://www.governmentjobs.com/careers/boiseid",
            "https://www.governmentjobs.com/careers/boiseid/jobs",
            "https://www.governmentjobs.com/careers/boston/jobs/5504395-0",
            "https://www.schooljobs.com/careers/boiseid/jobs/5504395-0",
            "https://user:password@www.governmentjobs.com/careers/boiseid/jobs/5504395-0",
            "javascript:alert(1)",
        )
        for url in rejected:
            with self.subTest(url=url):
                self.assertFalse(belongs_to_configured_agency(url,"boiseid","NEOGOV"))

    def test_valid_education_feed_own_agency_and_different_host(self):
        url="https://www.schooljobs.com/careers/centraldistrict/jobs/5504234-0/temporary"
        # Official vacancy route with a trailing slug is fine.
        self.assertTrue(belongs_to_configured_agency(
            url,"centraldistrict","NEOED Schooljobs"))
        self.assertFalse(belongs_to_configured_agency(
            url,"boiseid","NEOED Schooljobs"))
        self.assertFalse(belongs_to_configured_agency(
            url,"centraldistrict","NEOGOV"))

    def test_identical_vacancy_not_shown_three_times(self):
        rows=[
            {"title":"Accounts Payable Specialist II","company":"Charlotte County",
             "source":"NEOGOV","url":BOISE_AP},
            {"title":"Accounts Payable Specialist II","company":"City of Boise",
             "source":"NEOGOV","url":BOISE_AP+"?utm_source=feed"},
            {"title":"Accounts Payable Specialist II","company":"City of Boston",
             "source":"NEOGOV","url":BOISE_AP},
            {"title":"Accounts Receivable (AR) Analyst","company":"City of Boise",
             "source":"NEOGOV","url":BOISE_AR},
        ]
        result=dedupe_vacancy_urls(rows)
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]["url"],BOISE_AP)
        self.assertEqual(result[1]["url"],BOISE_AR)

    def test_keep_distinct_requisition_urls(self):
        rows=[
            {"title":"Operations Manager","source":"NEOGOV","url":BOISE_AP},
            {"title":"Operations Manager","source":"NEOGOV","url":BOISE_AR},
        ]
        self.assertEqual(len(dedupe_vacancy_urls(rows)),2)

    def test_loader_and_cached_ranker_both_enforce_agency(self):
        app=ast.parse(Path(__file__).with_name("app.py").read_text())
        functions={x.name:x for x in app.body if isinstance(x,ast.FunctionDef)}
        gov=ast.unparse(functions["load_neogov_feeds"])
        school=ast.unparse(functions["load_neoed_feeds"]) if "load_neoed_feeds" in functions else ""
        ranking=ast.unparse(functions["filter_and_rank_jobs"])
        self.assertIn("belongs_to_configured_agency",gov)
        self.assertIn("belongs_to_configured_agency",school)
        self.assertIn("dedupe_vacancy_urls",ranking)
        self.assertIn("belongs_to_configured_agency",ranking)


class FormalCredentialTests(unittest.TestCase):
    def test_actual_long_preferred_engineering_ops_business_degree(self):
        desc=("<h2>Qualifications</h2><li>Bachelor’s degree in Engineering, "
              "Operations Management, Business, Industrial Technology, "
              "or a related field is preferred.</li>")
        report=extract_formal_minimums(
            {"title":"Operations Manager (Second Shift)","description":desc},
            RESUME)
        self.assertEqual(report["ranking_caution"],0)
        self.assertFalse(report["unverified_mandatory"])
        self.assertTrue(any(c["priority"]=="Preferred / mentioned"
                            for c in report["checks"]))

    def test_preferred_degree_over_115_chars_no_penalty(self):
        desc=("<h2>Minimum Qualifications</h2><li>Bachelor's degree in "
              "engineering, industrial technology, business administration, "
              "industrial operations systems, supply chain management, or "
              "another field related to manufacturing and operations is preferred.</li>")
        q=extract_formal_minimums({"title":"Operations Manager","description":desc},RESUME)
        self.assertFalse(q["unverified_mandatory"])
        self.assertEqual(q["ranking_caution"],0)

    def test_inline_architecture_engineering_education_requires_field(self):
        text=(
            "Experienced project executive with federal facilities and client "
            "relations. EDUCATION and/or EXPERIENCE: "
            "• Bachelor’s degree in architecture or engineering, from "
            "an accredited four-year college or university."
        )
        q=extract_formal_minimums(
            {"title":"Federal Project Executive","description":text},
            RESUME)
        self.assertTrue(q["unverified_mandatory"],q)
        self.assertTrue(any("technical" in c["area"] and c["ranking_caution"]>0
                            for c in q["checks"]))
        fit=assess_job_qualifications(
            {"title":"Federal Project Executive","description":text},
            compile_resume_profile(RESUME,()),RESUME)
        self.assertLess(evidence_index(fit),90)

    def test_technical_degree_only_when_required(self):
        required=("<h2>Education and/or Experience</h2><li>Bachelor's degree "
                  "in Engineering is required for this position.</li>")
        preferred=("<h2>Qualifications</h2><li>Bachelor's degree in Engineering "
                   "is preferred for this position.</li>")
        self.assertGreater(extract_formal_minimums(
            {"title":"Operations Manager","description":required},RESUME)["ranking_caution"],0)
        self.assertEqual(extract_formal_minimums(
            {"title":"Operations Manager","description":preferred},RESUME)["ranking_caution"],0)

    def test_alternative_business_degree_respected(self):
        desc="<h2>Qualifications</h2><li>Bachelor's degree in engineering or business administration required.</li>"
        q=extract_formal_minimums(
            {"title":"Operations Manager","description":desc},RESUME)
        self.assertEqual(q["ranking_caution"],0)


if __name__=="__main__":
    unittest.main()
