"""UI-only regression checks for top navigation and reliable downloads.

Matching logic must not change as a side effect of the redesign.
"""
import ast
import csv
import io
import json
from pathlib import Path
import unittest

from ranked_breakdowns import breakdowns_csv_rows, breakdowns_json
from build_info import MATCHING_ENGINE_VERSION, export_filename
from ui_theme import APP_CSS,brand,listing_head


class NavigationAndDownloadsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path(__file__).with_name("app.py").read_text()
        cls.tree=ast.parse(cls.source)
        cls.functions={n.name:n for n in cls.tree.body
                       if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

    def test_navigation_is_top_level_horizontal_not_sidebar(self):
        self.assertNotIn("st.sidebar.radio",self.source)
        self.assertNotIn("st.sidebar.markdown",self.source)
        self.assertIn("key='top_navigation'",self.source)
        self.assertIn("horizontal=True",self.source)
        self.assertIn("brand(MATCHING_ENGINE_VERSION)",self.source)
        self.assertIn(".st-key-top_navigation",APP_CSS)

    def test_download_button_fragments_prevent_rerun(self):
        for name in ("ranked_exports","download_file_widget"):
            node=self.functions[name]
            self.assertTrue(any(isinstance(d,ast.Attribute) and
                isinstance(d.value,ast.Name) and d.value.id=="st" and
                d.attr=="fragment" for d in node.decorator_list))
            self.assertTrue(any(isinstance(call,ast.Call) and
                isinstance(call.func,ast.Attribute) and
                call.func.attr=="download_button" for call in ast.walk(node)))

    def test_ranked_download_not_conditioned_on_resume(self):
        # The builder accepts all_results, not resume_text, and the call
        # resides in Find Jobs' all_results branch without CV gating.
        source=self.source
        self.assertIn("ranked_exports(all_results,stats.get('run_id',''))",source)
        begin=source.index("if not all_results:")
        end=source.index("new_only=st.checkbox(",begin)
        section=source[begin:end]
        self.assertIn("ranked_exports(all_results",section)
        self.assertNotIn("if st.session_state.resume_text.strip():",section)
        self.assertIn("Download search results",source)

    def test_csv_and_json_have_working_files_without_resume(self):
        jobs=[
            {"title":"Regional Operations Director",
             "company":"Example & Co.","location":"Minot, ND",
             "url":"https://example.org/jobs/101",
             "government":False,"source":"Employer board",
             "work_style":"On-site","date":"2026-10-16",
             "qualification_match":None}
        ]
        run_id="20261016T123000Z"
        rows=breakdowns_csv_rows(jobs,MATCHING_ENGINE_VERSION,run_id)
        output=io.StringIO(newline="")
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        encoded=output.getvalue().encode("utf-8-sig")
        parsed=list(csv.DictReader(io.StringIO(encoded.decode("utf-8-sig"))))
        self.assertEqual(parsed[0]["Job title"],"Regional Operations Director")
        self.assertEqual(parsed[0]["Job URL"],jobs[0]["url"])
        self.assertEqual(parsed[0]["Employer"],"Example & Co.")
        self.assertEqual(parsed[0]["Comparative fit index (0-96; not hiring probability)"],"0")
        js=json.dumps(breakdowns_json(jobs,MATCHING_ENGINE_VERSION,run_id))
        self.assertEqual(json.loads(js)[0]["job_url"],jobs[0]["url"])
        self.assertTrue(export_filename("ranked",run_id,"csv").endswith(".csv"))
        self.assertTrue(export_filename("detailed",run_id,"json").endswith(".json"))

    def test_all_data_download_surfaces_use_fragment(self):
        self.assertIn("download_file_widget(",self.source)
        self.assertIn("'tracker_full_backup'",self.source)
        self.assertIn("'tracker_applications_csv'",self.source)
        self.assertIn("'career_matches_export'",self.source)
        self.assertIn("'approved_resume_wording'",self.source)

    def test_light_background_and_spacious_panels(self):
        self.assertIn("#F5F7F5",APP_CSS)
        self.assertIn("#FFFFFF",APP_CSS)
        self.assertIn("padding:1.5rem 1.65rem",APP_CSS)
        self.assertIn("AI Job Finder",brand(MATCHING_ENGINE_VERSION))
        self.assertNotIn("<img",brand(MATCHING_ENGINE_VERSION))
        self.assertIn("example",listing_head("example","Employer","US",
                                              "On-site",False))


if __name__=="__main__":
    unittest.main()
