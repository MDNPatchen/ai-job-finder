"""Production-export regression: (Remote) title cannot bypass Mayo-only filter."""
import ast
import unittest
from pathlib import Path
from job_workflow import explicitly_remote_title

class EmployerRemoteTitleTests(unittest.TestCase):
    def test_explicit_title_remote_markers(self):
        examples=[
            "Credentialing & Enrollment Program Analyst (Remote)",
            "Director of Operations [Remote]",
            "Finance Manager Fully Remote",
            "Legal Counsel Remote-only",
            "Analyst 100% remote",
        ]
        for title in examples:
            with self.subTest(title=title):
                self.assertTrue(explicitly_remote_title(title))
    def test_unrelated_title_not_remote(self):
        for title in ("Regional Operations Director",
                      "Remote Sensing Programs Manager",
                      "Field Remote Equipment Supervisor",
                      "Hybrid Operations Director"):
            with self.subTest(title=title):
                self.assertFalse(explicitly_remote_title(title))
    def test_both_ingest_and_filter_apply_title_rule(self):
        app=ast.parse(Path(__file__).with_name("app.py").read_text())
        functions={n.name:n for n in app.body if isinstance(n,ast.FunctionDef)}
        importer=ast.unparse(functions['standard_job'])
        filterer=ast.unparse(functions['filter_and_rank_jobs'])
        self.assertIn('explicitly_remote_title(title)',importer)
        self.assertIn("explicitly_remote_title(job.get('title'))",filterer)
        self.assertIn("arrangement = 'Remote'",filterer)
        self.assertIn("'Mayo Clinic'",filterer)

if __name__=="__main__":
    unittest.main()
