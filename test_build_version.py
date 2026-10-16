"""Ensure stale Streamlit matches and old downloads are clearly identified."""
import ast
import unittest
from pathlib import Path

from build_info import MATCHING_ENGINE_VERSION, needs_search_refresh, export_filename
from ranked_breakdowns import breakdowns_json, breakdowns_csv_rows


class ExportVersionTests(unittest.TestCase):
    def test_previous_engine_search_results_must_be_cleared(self):
        self.assertTrue(needs_search_refresh(None))
        self.assertTrue(needs_search_refresh("2.0"))
        self.assertTrue(needs_search_refresh("2.1"))
        self.assertFalse(needs_search_refresh(MATCHING_ENGINE_VERSION))

    def test_search_run_downloads_have_distinct_names(self):
        csv=export_filename("ranked","20261015T213500Z","csv")
        json_name=export_filename("detailed","20261015T213500Z","json")
        self.assertIn("_v317_",csv)
        self.assertIn("20261015T213500Z",csv)
        self.assertNotEqual(csv,json_name)
        self.assertNotEqual(csv,export_filename("ranked","20261015T213600Z","csv"))

    def test_export_name_rejects_unsafe_format(self):
        with self.assertRaises(ValueError):
            export_filename("ranked","run","xlsx")

    def test_json_csv_match_same_version_and_run(self):
        job={
            'title':'Director of Operations','company':'Example Employer',
            'source':'Workable employer','url':'https://example.org/job',
            'qualification_match':{'resume_present':True,'fit_index':89,
                                   'label':'Strong evidence overlap',
                                   'resume_matches':[],'confirmed_only':[],
                                   'not_documented':[],'screeners':[],
                                   'total_areas':0,'resume_focus':''}
        }
        run="20261015T213500Z"
        data=breakdowns_json([job],MATCHING_ENGINE_VERSION,run)
        rows=breakdowns_csv_rows([job],MATCHING_ENGINE_VERSION,run)
        self.assertEqual(rows[0]['Matching engine version'],data[0]['matching_engine_version'])
        self.assertEqual(rows[0]['Search run ID (UTC)'],run)
        self.assertEqual(rows[0]['Comparative fit index (0-96; not hiring probability)'],
                         data[0]['comparative_fit_index'])

    def test_streamlit_app_uses_versioned_ranking_and_files(self):
        src=Path(__file__).with_name("app.py").read_text(encoding="utf-8")
        ast.parse(src)
        self.assertIn("st.session_state.pop('search_results', None)",src)
        self.assertIn("needs_search_refresh(st.session_state.get('matching_engine_version'))",src)
        self.assertIn("export_filename('ranked',run_id,'csv')",src)
        self.assertIn("export_filename('detailed',run_id,'json')",src)


if __name__=="__main__":
    unittest.main()
