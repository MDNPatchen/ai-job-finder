"""Offline tests for workplace arrangements and supporting export evidence.

Do not require Streamlit, provider credentials or outside HTTP.
"""
import ast
from pathlib import Path
import re
import unittest

from posting_metadata import (
    affirmative, declared_arrangement, from_explicit_description,
    strict_onsite_requirement,
    employer_identity_kind, reconcile_workplace_record,
    NO_WORKPLACE_EVIDENCE, WORKPLACE_SOURCE_UNVERIFIED
)
from ranked_breakdowns import breakdowns_csv_rows, breakdowns_json
from job_workflow import explicitly_remote_title


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
        'strict_onsite_requirement':strict_onsite_requirement,
        'html_to_text':lambda raw:re.sub(r'<[^>]+>',' ',str(raw or '')),
        'employer_identity_kind':employer_identity_kind,
        'explicitly_remote_title':explicitly_remote_title,
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

    def test_cached_unknown_cannot_claim_posting_evidence(self):
        cached={'work_style':'Not specified','remote':False,
                'arrangement_source':'Posting location or description text',
                'location':'Nashville, TN','description':'Lead business operations.'}
        repaired=reconcile_workplace_record(cached)
        self.assertEqual(repaired['work_style'],'Not specified')
        self.assertEqual(repaired['arrangement_source'],NO_WORKPLACE_EVIDENCE)
        self.assertEqual(cached['arrangement_source'],
                         'Posting location or description text')

    def test_cached_hybrid_without_traceable_source_is_marked_unverified(self):
        cached={'work_style':'Hybrid','remote':False,
                'arrangement_source':'No explicit workplace label in public posting',
                'location':'Nashville, TN','description':'Manage the school budget.'}
        repaired=reconcile_workplace_record(cached)
        self.assertEqual(repaired['work_style'],'Hybrid')
        self.assertEqual(repaired['arrangement_source'],WORKPLACE_SOURCE_UNVERIFIED)

    def test_cached_hybrid_evidence_is_recovered_if_explicit_in_posting(self):
        cached={'work_style':'Hybrid','remote':False,
                'arrangement_source':'No explicit workplace label in public posting',
                'location':'Nashville, TN',
                'description':'Work arrangement: Hybrid. Lead operational teams.'}
        repaired=reconcile_workplace_record(cached)
        self.assertEqual(repaired['work_style'],'Hybrid')
        self.assertEqual(repaired['arrangement_source'],
                         'Posting location or description text')

    def test_cached_known_ats_label_is_not_erased(self):
        cached={'work_style':'On-site',
                'arrangement_source':'Employer ATS workplace label',
                'remote':False,'location':'Salt Lake City, UT'}
        repaired=reconcile_workplace_record(cached)
        self.assertEqual(repaired['arrangement_source'],
                         'Employer ATS workplace label')

    def test_cached_provider_remote_label_requires_evidence(self):
        cached={'work_style':'Remote','remote':True,
                'arrangement_source':'Provider remote flag',
                'location':'Rochester, Minnesota'}
        repaired=reconcile_workplace_record(cached)
        self.assertEqual(repaired['work_style'],'Remote')
        self.assertEqual(repaired['arrangement_source'],'Provider remote flag')

    def test_inconsistent_cached_provenance_repairs_before_export(self):
        cached={'work_style':'Not specified','remote':False,
                'arrangement_source':'Posting location or description text',
                'location':'United States','description':'Direct operational leaders.',
                'title':'Director of Operations','company':'Example Inc',
                'source':'NEOGOV','url':'https://example.org/director',
                'qualification_match':{'resume_present':True,'fit_index':78}}
        repaired=reconcile_workplace_record(cached)
        report=breakdowns_csv_rows([repaired])[0]
        self.assertEqual(report['Work arrangement'],'Not specified')
        self.assertEqual(report['Work arrangement evidence'],NO_WORKPLACE_EVIDENCE)

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
