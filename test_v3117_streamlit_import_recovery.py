"""Startup hotfix: tolerate an outdated Streamlit-cached job_workflow module.

Verify the exact missing helper symptom without relying on a live network or
an installed Streamlit instance. Validate both shared function and fallback.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

import job_workflow


def app_local_remote_policy(namespace):
    source=Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    assert any(isinstance(n,ast.Import) and
               any(x.name=="job_workflow" and x.asname=="_job_workflow"
                   for x in n.names) for n in tree.body)
    assert not any(isinstance(n,ast.ImportFrom) and n.module=="job_workflow"
                   and any(x.name=="permitted_remote_source" for x in n.names)
                   for n in tree.body)
    fn=next(n for n in tree.body
            if isinstance(n,ast.FunctionDef)
            and n.name=="permitted_remote_source")
    result={}
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=[fn],type_ignores=[])),"app.py","exec"),
        {"_job_workflow":namespace},result)
    return result["permitted_remote_source"]


class SafeStreamlitImportTests(unittest.TestCase):
    def setUp(self):
        self.mayo={
            "source":"Mayo Clinic","company":"Mayo Clinic","government":False}
        self.gov={
            "source":"NEOGOV","company":"City of Boise","government":True}
        self.school={
            "source":"NEOED Schooljobs","company":"School District","government":True}
        self.nyc={
            "source":"NYC Open Data","company":"NYC Agency","government":True}
        self.private={
            "source":"Greenhouse","company":"Private Employer","government":False}

    def test_missing_new_helper_does_not_cause_import_error(self):
        # Simulate Streamlit publishing new app.py while old job_workflow.py
        # remains in its Python import cache and lacks the newer symbol.
        policy=app_local_remote_policy(SimpleNamespace())
        self.assertTrue(policy(self.mayo))
        for job in (self.gov,self.school,self.nyc):
            self.assertTrue(policy(job))
        self.assertFalse(policy(self.private))
        self.assertFalse(policy({**self.private,"government":True}))
        self.assertFalse(policy({**self.gov,"government":False}))

    def test_current_module_prefers_shared_policy(self):
        policy=app_local_remote_policy(job_workflow)
        for job in (self.mayo,self.gov,self.school,self.nyc,self.private):
            self.assertEqual(policy(job),job_workflow.permitted_remote_source(job))

    def test_missing_symbol_can_be_recovered_without_changing_search_logic(self):
        called=[]
        def alternate(job):
            called.append(job)
            return bool(job.get("allow_for_test"))
        policy=app_local_remote_policy(SimpleNamespace(permitted_remote_source=alternate))
        self.assertTrue(policy({"allow_for_test":True}))
        self.assertEqual(len(called),1)


if __name__=="__main__":
    unittest.main()
