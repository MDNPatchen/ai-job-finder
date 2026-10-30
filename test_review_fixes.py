"""Regressions for the October 2026 code review fixes."""
import ast
import io
import json
import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import tracker_store
from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index
from source_http import fetch_json
from tracker_store import UnlockThrottle, make_workspace
from workspace_merge import merge_workspaces

APP = Path(__file__).with_name('app.py').read_text(encoding='utf-8')


def app_function(name, env):
    tree = ast.parse(APP)
    func = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == name)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[])),
                 'app.py', 'exec'), env)
    return env[name]


def tracked(status):
    return {'Company': 'Acme', 'Job Title': 'GM', 'Location': 'Minot, ND',
            'Job URL': '', 'Status': status}


class KeywordMatchTests(unittest.TestCase):
    def score(self, title, query):
        score_job = app_function('score_job', {
            're': re,
            'role_classification': lambda title: ('Leadership', 10),
            'SPECIALIST_EXCLUSIONS': re.compile('never-matches'),
            'compile_resume_profile': compile_resume_profile,
            'verified_competencies': lambda: set(),
            'assess_job_qualifications': assess_job_qualifications,
            'evidence_index': evidence_index,
            'states_in_location': lambda location: ['ND'],
        })
        job = {'title': title, 'description': 'Prepare meals for guests.',
               'government': False, 'location': 'Minot, ND'}
        return score_job(job, 'Managed operations and budgets.', query)

    def test_keyword_does_not_match_inside_another_word(self):
        self.assertIsNone(self.score('Line Cook', 'COO'))
        self.assertIsNone(self.score('Restart Coordinator', 'art'))

    def test_keyword_still_matches_whole_word(self):
        self.assertIsNotNone(self.score('COO and General Manager', 'COO'))


class MergeDuplicateTests(unittest.TestCase):
    def test_duplicate_rows_survive_merge(self):
        local = make_workspace([tracked('Saved'), tracked('Applied')])
        merged, conflicts = merge_workspaces(make_workspace(), local, make_workspace())
        self.assertEqual(conflicts, [])
        self.assertCountEqual([r['Status'] for r in merged['jobs']], ['Saved', 'Applied'])
        self.assertEqual(len(merged['job_keys']), 2)

    def test_edit_to_second_duplicate_is_kept(self):
        base = make_workspace([tracked('Saved'), tracked('Saved')])
        local = make_workspace([tracked('Saved'), tracked('Interviewing')])
        merged, conflicts = merge_workspaces(base, local, base)
        self.assertEqual(conflicts, [])
        self.assertCountEqual([r['Status'] for r in merged['jobs']], ['Saved', 'Interviewing'])


class UsajobsTests(unittest.TestCase):
    def test_typed_keyword_replaces_default_titles(self):
        terms = app_function('usajobs_terms', {'USAJOBS_DEFAULT_TERMS': ('a', 'b')})
        self.assertEqual(terms(('budget analyst',)), ('budget analyst',))
        self.assertEqual(terms(('',)), ('a', 'b'))
        self.assertEqual(terms(()), ('a', 'b'))

    def test_fetch_json_sends_extra_headers(self):
        seen = {}

        def opener(request, timeout):
            seen.update(request.header_items())
            response = MagicMock()
            response.__enter__.return_value = io.BytesIO(json.dumps({'ok': 1}).encode())
            return response

        self.assertEqual(fetch_json('https://example.org', opener=opener,
                                    headers={'Authorization-Key': 'k'}), {'ok': 1})
        self.assertEqual(seen.get('Authorization-key'), 'k')
        self.assertEqual(seen.get('Accept'), 'application/json')


class UnlockThrottleTests(unittest.TestCase):
    def test_locks_after_repeated_failures_then_recovers(self):
        now = [0.0]
        throttle = UnlockThrottle(max_failures=3, lockout_seconds=60, clock=lambda: now[0])
        for _ in range(2):
            throttle.record(False)
        self.assertEqual(throttle.seconds_remaining(), 0)
        throttle.record(False)
        self.assertEqual(throttle.seconds_remaining(), 60)
        now[0] = 61
        self.assertEqual(throttle.seconds_remaining(), 0)
        throttle.record(True)
        throttle.record(False)
        self.assertEqual(throttle.seconds_remaining(), 0)


class SchemaOnceTests(unittest.TestCase):
    def test_schema_runs_once_per_database(self):
        tracker_store._schema_ready.clear()
        cur = MagicMock()
        tracker_store._schema(cur, 'postgres://example/db')
        first = cur.execute.call_count
        tracker_store._schema(cur, 'postgres://example/db')
        self.assertEqual(cur.execute.call_count, first)
        cur.connection.commit.assert_called_once()
        tracker_store._schema(cur, 'postgres://example/other')
        self.assertEqual(cur.execute.call_count, first * 2)
        tracker_store._schema_ready.clear()


class PaginationTests(unittest.TestCase):
    def test_partial_updates_do_not_reset_page(self):
        tree = ast.parse(APP)
        func = next(x for x in tree.body if isinstance(x, ast.FunctionDef)
                    and x.name == 'consume_search_update')
        self.assertNotIn('search_page', ast.unparse(func))


if __name__ == '__main__':
    unittest.main()
