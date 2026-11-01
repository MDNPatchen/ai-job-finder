"""Career profile answers (and opt-in resume text) are saved with the tracker."""
import json
import unittest

from career_profile import LEGACY_DEFAULT_ANSWERS
from tracker_store import (clean_profile, export_workspace_json, import_workspace_json,
                           make_workspace, workspace_digest)
from workspace_merge import merge_profile, merge_workspaces
from workspace_recovery import prepare_restore

ROW = {'Company': 'Acme', 'Job Title': 'General Manager', 'Status': 'Saved'}
ANSWERS = {'pnl': 'Yes', 'ad_sales': 'No', 'sites': 6, 'budget_usd': 14000000}


class ProfileStorageTests(unittest.TestCase):
    def test_answers_round_trip_through_backup(self):
        raw = export_workspace_json([ROW], [], True, {}, {'answers': ANSWERS})
        restored = import_workspace_json(raw.encode())
        self.assertEqual(restored['profile']['answers'], ANSWERS)
        self.assertNotIn('resume_text', raw)

    def test_resume_only_saved_when_provided(self):
        raw = export_workspace_json([ROW], [], True, {}, {'answers': ANSWERS, 'resume_text': 'Led five newspapers.'})
        self.assertEqual(import_workspace_json(raw.encode())['profile']['resume_text'], 'Led five newspapers.')

    def test_older_backups_without_profile_still_pass_integrity(self):
        old = {'schema_version': 2, 'jobs': [ROW], 'seen': [], 'has_baseline': True, 'employer_evidence': {}}
        old['integrity_sha256'] = workspace_digest(old)
        restored = import_workspace_json(json.dumps(old).encode())
        self.assertEqual(restored['profile'], {'answers': {}})

    def test_tampered_profile_fails_integrity(self):
        payload = json.loads(export_workspace_json([ROW], [], True, {}, {'answers': ANSWERS}))
        payload['profile']['answers']['ad_sales'] = 'Yes'
        with self.assertRaises(ValueError):
            import_workspace_json(json.dumps(payload).encode())

    def test_malformed_answers_are_dropped_not_fatal(self):
        clean = clean_profile({'answers': {'pnl': 'Yes', 'Bad Key': 'x', 'sites': -3, 'flag': True,
                                           'long': 'x' * 50, 'ok_number': 4.0}})
        self.assertEqual(clean, {'answers': {'pnl': 'Yes', 'ok_number': 4}})
        with self.assertRaises(ValueError):
            clean_profile({'answers': 'yes'})

    def test_resume_text_is_capped(self):
        self.assertEqual(len(clean_profile({'resume_text': 'a' * 90000})['resume_text']), 60000)


class ProfileMergeTests(unittest.TestCase):
    def test_unlocking_a_fresh_session_takes_the_saved_profile(self):
        local = {'answers': dict(LEGACY_DEFAULT_ANSWERS)}           # untouched defaults
        remote = {'answers': ANSWERS, 'resume_text': 'Saved resume'}
        self.assertEqual(merge_profile({}, local, remote), {'answers': ANSWERS, 'resume_text': 'Saved resume'})

    def test_edits_in_this_session_win(self):
        base = {'answers': ANSWERS}
        local = {'answers': {**ANSWERS, 'ad_sales': 'Yes'}, 'resume_text': 'New resume'}
        remote = {'answers': ANSWERS, 'resume_text': 'Old resume'}
        merged = merge_profile(base, local, remote)
        self.assertEqual(merged['answers']['ad_sales'], 'Yes')
        self.assertEqual(merged['resume_text'], 'New resume')

    def test_remote_change_kept_when_this_session_did_not_change(self):
        base = {'answers': ANSWERS}
        remote = {'answers': {**ANSWERS, 'sites': 8}}
        self.assertEqual(merge_profile(base, base, remote)['answers']['sites'], 8)

    def test_full_workspace_merge_carries_profile(self):
        base = make_workspace([ROW])
        local = make_workspace([ROW], profile={'answers': dict(LEGACY_DEFAULT_ANSWERS)})
        remote = make_workspace([ROW], profile={'answers': ANSWERS})
        merged, conflicts = merge_workspaces(base, local, remote)
        self.assertEqual(conflicts, [])
        self.assertEqual(merged['profile']['answers'], ANSWERS)

    def test_restore_merge_keeps_current_profile_and_fills_from_backup(self):
        current = make_workspace([ROW], profile={'answers': {'pnl': 'No'}})
        incoming = make_workspace([], profile={'answers': ANSWERS})
        staged, _ = prepare_restore(current, incoming)
        self.assertEqual(staged['profile']['answers'], {'pnl': 'No'})
        empty_now = make_workspace([ROW])
        staged, _ = prepare_restore(empty_now, incoming)
        self.assertEqual(staged['profile']['answers'], ANSWERS)


class SessionApplyTests(unittest.TestCase):
    """tracker_sync needs Streamlit; skipped where it is not installed."""
    @classmethod
    def setUpClass(cls):
        try:
            import tracker_sync
        except ImportError as exc:  # pragma: no cover - CI installs Streamlit
            raise unittest.SkipTest(str(exc))
        cls.sync = tracker_sync

    def state(self, **extra):
        return {'jobs': [], 'seen_jobs': [], 'search_baseline': False, 'employer_checks': {},
                'profile_answers': dict(LEGACY_DEFAULT_ANSWERS), 'resume_text': 'Session resume', **extra}

    def test_snapshot_excludes_resume_unless_opted_in(self):
        self.assertNotIn('resume_text', self.sync.snapshot(self.state())['profile'])
        opted = self.sync.snapshot(self.state(save_resume_with_tracker=True))['profile']
        self.assertEqual(opted['resume_text'], 'Session resume')

    def test_apply_sets_saved_profile_and_clears_stale_widgets(self):
        state = self.state(profile_pnl='Not sure', search_results=[1], search_stats={})
        data = make_workspace([ROW], profile={'answers': ANSWERS, 'resume_text': 'Saved resume'})
        self.sync.apply_workspace(state, data)
        self.assertEqual(state['profile_answers'], ANSWERS)
        self.assertEqual(state['resume_text'], 'Saved resume')
        self.assertTrue(state['save_resume_with_tracker'])
        self.assertNotIn('profile_pnl', state)
        self.assertNotIn('search_results', state)

    def test_apply_with_empty_profile_keeps_session_values(self):
        state = self.state()
        self.sync.apply_workspace(state, make_workspace([ROW]))
        self.assertEqual(state['profile_answers'], LEGACY_DEFAULT_ANSWERS)
        self.assertEqual(state['resume_text'], 'Session resume')


if __name__ == '__main__':
    unittest.main()
