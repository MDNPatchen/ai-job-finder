import unittest

from mayo_source import fetch_mayo_jobs, parse_detail, parse_page

ROOT = "https://jobs.mayoclinic.org"
LISTING = """
<section id='search-results'>
  <li><a href='/job/rochester/senior-director-mcl-operations/33647/101672780320'
         data-job-id='101672780320'><h2>Senior Director-MCL Operations</h2>
       <span>Rochester, Minnesota</span></a></li>
  <li><a href='/job/rochester/manager-practice-operations/33647/97565191712'>
       <h2>Manager - Practice Operations</h2></a></li>
</section>
"""
DETAIL = """
<h1>Senior Director-MCL Operations</h1>
<p>Job ID 392987 Date posted 10/07/2026</p>
<ul><li>Rochester, Minnesota</li></ul>
<p>Remote: No</p>
<h2>Responsibilities</h2><p>Leading operations teams and budgets.</p>
"""


class MayoSourceTests(unittest.TestCase):
    def test_two_public_search_links(self):
        page = parse_page(LISTING)
        self.assertEqual(len(page.links), 2)
        self.assertTrue(all("/job/" in url for url, _ in page.links))

    def test_reject_external_and_non_mayo_links(self):
        html = """<a href='https://other.example/job/rochester/a/33647/111'>bad</a>
                  <a href='/job/rochester/a/33647/111'>good</a>"""
        self.assertEqual(len(parse_page(html).links), 1)

    def test_date_is_iso_format_and_work_style_unspecified(self):
        job = parse_detail(DETAIL, ROOT + "/job/rochester/senior-director-mcl-operations/33647/101672780320")
        self.assertEqual(job["date"], "2026-10-07")
        self.assertEqual(job["location"], "Rochester, MN")
        self.assertEqual(job["work_style"], "")

    def test_hybrid_overrides_remote_no(self):
        data = DETAIL.replace("Remote: No", "Remote: No. This is a hybrid position.")
        self.assertEqual(parse_detail(data, ROOT + "/job/rochester/a/33647/111")["work_style"], "Hybrid")

    def test_identified_remote_is_excluded_later(self):
        data = DETAIL.replace("Remote: No", "Remote: Yes")
        self.assertEqual(parse_detail(data, ROOT + "/job/rochester/a/33647/111")["work_style"], "Remote")

    def test_bounded_search_and_detail_fetch(self):
        calls = []
        def fake(url):
            calls.append(url)
            return LISTING if "/search-jobs?" in url else DETAIL
        result = fetch_mayo_jobs(fake)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(calls), 7)
        self.assertTrue(all(x["date"] == "2026-10-07" for x in result))


if __name__ == "__main__":
    unittest.main()
