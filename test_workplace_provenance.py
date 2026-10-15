"""Offline tests for workplace arrangements and supporting export evidence.

Do not require Streamlit, provider credentials or outside HTTP.
"""
import ast
from pathlib import Path
import re
import unittest

from posting_metadata import (
    affirmative, declared_arrangement, from_explicit_description,
    employer_identity_kind
)
from ranked_breakdowns import breakdowns_csv_rows, breakdowns_json


def extract_current_functions():
    text=Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    tree=ast.parse(text)
    fn_names=('classify_work_arrangement','standard_job')
    nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in fn_names]
    assert len(nodes)==2
    module=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]))
    env={
        're':re,
        'declared_arrangement':declared_arrangement,
        'affirmative':affirmative,
        'from_explicit_description':from_explicit_description,
        'html_to_text':lambda raw:re.sub(r'<[^>]+>',' ',str(raw or '')),
        'employer_identity_kind':employer_identity_kind,
        'parse_posted_date':lambda value:None
    }
    exec(compile(module,'app.py','exec'),env)
    return env


def job(env, **kwargs):
    return env['standard_job'](
        'Director of Operations',
        'Example Employer',
        'https://jobs.example.org/director',
        kwargs.pop('location','Salt Lake City, Utah, United States'),
        kwargs.pop('description','Operations and finance leadership.'),
        'Workable employer',
        **kwargs
    )


class ArrangementProvenanceTests(unittest.TestCase):
    def test_unknown_location_normalizes_not_specified(self):
        env=extract_current_functions()
        listing=job(env)
        self.assertEqual(listing['work_style'],'Not specified')
        self.assertEqual(listing['arrangement_source'],
                         'No explicit workplace label in public posting')
        self.assertFalse(listing['remote'])

    def test_provider_on_site_label_has_provenance(self):
        listing=job(extract_current_functions(),declared_style='ONSITE')
        self.assertEqual(listing['work_style'],'On-site')
        self.assertEqual(listing['arrangement_source'],'Employer ATS workplace label')

    def test_posting_provides_on_site_requirement(self):
        listing=job(extract_current_functions(),
                    description='This is an on-site position.')
        self.assertEqual(listing['work_style'],'On-site')
        self.assertEqual(listing['arrangement_source'],
                         'Posting location or description text')

    def test_remote_flag_provenance_is_provider_not_posting(self):
        listing=job(extract_current_functions(),remote=True)
        self.assertEqual(listing['work_style'],'Remote')
        self.assertEqual(listing['arrangement_source'],'Provider remote flag')

    def test_declared_hybrid_beats_stale_remote_flag(self):
        listing=job(extract_current_functions(),remote=True,declared_style='HYBRID')
        self.assertEqual(listing['work_style'],'Hybrid')
        self.assertEqual(listing['arrangement_source'],'Employer ATS workplace label')

    def test_unknown_export_keeps_unknown_source(self):
        listing=job(extract_current_functions())
        listing['qualification_match']={'resume_present':True,'fit_index':77}
        result=breakdowns_csv_rows([listing])[0]
        self.assertEqual(result['Work arrangement'],'Not specified')
        self.assertEqual(result['Work arrangement evidence'],
                         'No explicit workplace label in public posting')
        self.assertEqual(breakdowns_json([listing])[0]['work_arrangement_source'],
                         result['Work arrangement evidence'])


if __name__=='__main__':
    unittest.main()
