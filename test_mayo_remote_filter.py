"""Regression tests for Mayo-only remote permission without importing Streamlit UI."""
import ast
import copy
from collections import Counter
from pathlib import Path
import unittest


APP_PATH = Path(__file__).with_name("app.py")
TREE = ast.parse(APP_PATH.read_text(encoding="utf-8"))


def isolated_function(name, globals_):
    for node in TREE.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            fn = copy.deepcopy(node)
            fn.decorator_list = []
            program = ast.Module(body=[fn], type_ignores=[])
            namespace = dict(globals_)
            exec(compile(ast.fix_missing_locations(program), str(APP_PATH), "exec"), namespace)
            return namespace[name]
    raise AssertionError("Missing function: " + name)


def job(title, source, arrangement, location="Rochester, MN"):
    return {"title": title, "company": "Mayo Clinic" if source == "Mayo Clinic" else "Other Employer",
            "source": source, "date": "2026-10-10", "work_style": arrangement,
            "remote": arrangement == "Remote", "location": location, "eligible": True,
            "description": "", "government": False, "url": "https://jobs.example/" + title.replace(" ", "-")}


def filter_jobs(data, state=None, mode="On-site + Hybrid"):
    function = isolated_function("filter_and_rank_jobs", {
        "Counter": Counter,
        "is_recent_posting": lambda j: True,
        "states_in_location": lambda loc: ["AZ"] if loc.endswith(", AZ") else ["MN"],
        "normalized_key": lambda j: (j["title"], j["company"]),
        "score_job": lambda j, resume, query: {**j, "rank": 10},
    })
    return function(data, state, mode, "", "")[0]


class MayoRemoteOnlyTests(unittest.TestCase):
    def test_mayo_remote_allowed_but_other_remote_excluded(self):
        results = filter_jobs([
            job("Director, remote Mayo", "Mayo Clinic", "Remote"),
            job("Director, remote other", "Greenhouse", "Remote"),
            job("Director, on site", "Greenhouse", "On-site"),
            job("Director, Mayo hybrid", "Mayo Clinic", "Hybrid"),
        ])
        titles = {j["title"] for j in results}
        self.assertIn("Director, remote Mayo", titles)
        self.assertIn("Director, Mayo hybrid", titles)
        self.assertIn("Director, on site", titles)
        self.assertNotIn("Director, remote other", titles)

    def test_explicit_modes_stay_strict(self):
        source = [job("Mayo remote", "Mayo Clinic", "Remote"),
                  job("Mayo onsite", "Mayo Clinic", "On-site"),
                  job("Mayo hybrid", "Mayo Clinic", "Hybrid")]
        self.assertEqual([j["title"] for j in filter_jobs(source, mode="On-site only")], ["Mayo onsite"])
        self.assertEqual([j["title"] for j in filter_jobs(source, mode="Hybrid only")], ["Mayo hybrid"])

    def test_state_limit_remains_respected(self):
        source = [job("Mayo remote AZ", "Mayo Clinic", "Remote", "Phoenix, AZ"),
                  job("Mayo remote MN", "Mayo Clinic", "Remote", "Rochester, MN")]
        self.assertEqual([j["title"] for j in filter_jobs(source, state="MN")], ["Mayo remote MN"])

    def test_mayo_may_show_more_than_three_roles(self):
        jobs = [job(f"Mayo director {i}", "Mayo Clinic", "Remote") for i in range(12)]
        self.assertEqual(len(filter_jobs(jobs)), 10)

    def test_source_must_match_not_just_employer_name(self):
        duplicate = job("Director of operations", "Greenhouse", "Remote")
        duplicate["company"] = "Mayo Clinic"
        self.assertEqual(filter_jobs([duplicate]), [])

    def test_mayo_loader_retains_remote_jobs(self):
        import mayo_source
        original = mayo_source.fetch_mayo_jobs
        mayo_source.fetch_mayo_jobs = lambda: [{
            "title": "Remote operations director", "url": "https://jobs.mayoclinic.org/job/rochester/remote/33647/123",
            "work_style": "Remote", "location": "Rochester, MN", "description": "Remote: Yes",
            "date": "2026-10-10", "salary": ""}]
        try:
            loader = isolated_function("load_mayo_clinic", {
                "MAYO_BOARDS": (("mayo-clinic", "Mayo Clinic"),),
                "standard_job": lambda title, company, url, location, description, source,
                   salary="", posted=None, declared_style="", eligible=True:
                    {"title": title, "company": company, "url": url, "location": location,
                     "source": source, "work_style": declared_style, "date": posted}
            })
            loaded = loader("test-catalog")
        finally:
            mayo_source.fetch_mayo_jobs = original
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["work_style"], "Remote")


if __name__ == "__main__":
    unittest.main()
