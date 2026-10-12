"""Offline NYC Open Data integration checks; public rows are mocked, no HTTP."""
import ast
import copy
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import re
import unittest
from urllib.parse import urlencode


def load_nyc_from_rows(rows):
    text=Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
              and n.name=='load_nyc_jobs')
    node=copy.deepcopy(node)
    node.decorator_list=[]
    namespace={
        'fetch_json':lambda url:rows,
        'urlencode':urlencode,'re':re,
        'datetime':datetime,'timezone':timezone,
        'states_in_location':lambda loc:['NY'] if 'NY' in loc else [],
        'parse_posted_date':lambda value:date.fromisoformat(value) if value else None,
        'standard_job':lambda title,company,url,location,description,source,
                              salary='',posted=None,gov=False:{
                                  'title':title,'company':company,'url':url,
                                  'location':location,'description':description,
                                  'source':source,'date':posted,'government':gov,
                              },
    }
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=[node],type_ignores=[])),'app.py','exec'),namespace)
    return namespace['load_nyc_jobs']()


def fake_record(**extra):
    body={'job_id':'901001', 'business_title':'Director of Operations',
          'agency':'TRANSPORTATION', 'posting_type':'External',
          'posting_date':date.today().isoformat(),
          'work_location':'Queens NY',
          'job_description':'Lead operational teams and budgets.',
          'minimum_qual_requirements':'Bachelor’s degree required. Six (6) years of public transportation management experience.',
          'preferred_skills':'Stakeholder engagement',
          'additional_information':'Emergency on-call availability',
          'to_apply':'Search Job ID at the city portal'}
    body.update(extra)
    return body


class NYCDataTests(unittest.TestCase):
    def test_keeps_minimum_qualifications_even_if_description_present(self):
        jobs=load_nyc_from_rows([fake_record()])
        self.assertEqual(len(jobs),1)
        self.assertIn('MINIMUM QUALIFICATIONS',jobs[0]['description'])
        self.assertIn('Six (6) years',jobs[0]['description'])
        self.assertIn('JOB DESCRIPTION',jobs[0]['description'])
        self.assertIn('PREFERRED SKILLS',jobs[0]['description'])

    def test_generic_portal_is_labeled_as_directory_not_direct_job(self):
        job=load_nyc_from_rows([fake_record()])[0]
        self.assertEqual(job['url'],'https://cityjobs.nyc.gov/jobs')
        self.assertIn('search by ID',job['posting_link_kind'])
        self.assertIn('901001',job['reference'])

    def test_explicit_actual_application_url_is_preserved(self):
        direct='https://cityjobs.nyc.gov/job/recruitment-coordinator-in-manhattan-jid-46927'
        job=load_nyc_from_rows([fake_record(to_apply='Apply at '+direct)])[0]
        self.assertEqual(job['url'],direct)
        self.assertIn('URL provided',job['posting_link_kind'])

    def test_explicitly_past_deadline_is_removed(self):
        past=(date.today()-timedelta(days=1)).isoformat()
        good=(date.today()+timedelta(days=20)).isoformat()
        jobs=load_nyc_from_rows([
            fake_record(post_until=past,job_id='old'),
            fake_record(post_until=good,job_id='new')])
        self.assertEqual(len(jobs),1)
        self.assertIn('new',jobs[0]['reference'])

if __name__=='__main__':
    unittest.main()
