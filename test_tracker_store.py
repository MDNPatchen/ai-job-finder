"""Session backups, import validation and authorization regressions (offline)."""
import csv
import io
import json
import unittest

from tracker_store import (
    STATUSES, COLUMNS, normalize_tracker_row, import_tracker_csv,
    export_tracker_csv, import_workspace_json, export_workspace_json,
    make_workspace, authenticate, clean_seen
)

ROW={
    'Company':'Example Media','Job Title':'Director of Operations',
    'Location':'Fargo, ND','Job URL':'https://jobs.example.com/123',
    'Salary':'$125,000 Annually','Status':'Applied',
    'Date Recorded':'2026-10-15','Interview Date':'','Notes':'Follow-up next week',
}


class TrackerStoreTests(unittest.TestCase):
    def test_csv_roundtrip_restores_application_state(self):
        csv_data=export_tracker_csv([ROW])
        imported=import_tracker_csv(csv_data.encode('utf-8'))
        self.assertEqual(imported,[ROW])

    def test_json_roundtrip_carries_prior_job_history(self):
        seen=['a'*32,'b'*32]
        output=export_workspace_json([ROW],seen,True)
        restored=import_workspace_json(output.encode('utf-8'))
        self.assertEqual(restored['jobs'],[ROW])
        self.assertEqual(restored['seen'],seen)
        self.assertTrue(restored['has_baseline'])

    def test_older_csv_from_original_tracker_is_accepted(self):
        buffer=io.StringIO()
        writer=csv.DictWriter(buffer,fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(ROW)
        restored=import_tracker_csv(buffer.getvalue().encode())
        self.assertEqual(restored[0]['Status'],'Applied')

    def test_csv_formula_injection_is_escaped(self):
        malicious={**ROW,'Company':'=HYPERLINK("bad")'}
        output=export_tracker_csv([malicious])
        self.assertIn("'=HYPERLINK",output)

    def test_non_http_application_link_rejected(self):
        with self.assertRaises(ValueError):
            normalize_tracker_row({**ROW,'Job URL':'javascript:alert(1)'})

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            normalize_tracker_row({**ROW,'Status':'Administrator'})

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            normalize_tracker_row({**ROW,'Interview Date':'tomorrow'})

    def test_import_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            import_tracker_csv(b'Company,Job Title\nExample,A role\n')

    def test_never_import_more_than_fixed_size(self):
        with self.assertRaises(ValueError):
            import_tracker_csv(b'x' * 5_000_001)

    def test_unknown_json_backup_version_rejected(self):
        with self.assertRaises(ValueError):
            import_workspace_json(json.dumps({'schema_version':999}).encode())

    def test_seen_history_only_allows_hashes(self):
        ids=clean_seen(['a'*32,'a'*32,'not-a-hash'])
        self.assertEqual(ids,['a'*32])

    def test_password_requires_long_exact_secret(self):
        self.assertFalse(authenticate('secret','secret'))
        self.assertTrue(authenticate('an-access-key-123','an-access-key-123'))
        self.assertFalse(authenticate('an-access-key-124','an-access-key-123'))

    def test_backup_rejects_too_many_tracked_jobs(self):
        with self.assertRaises(ValueError):
            make_workspace([ROW]*5001,[],False)

    def test_status_values_preserved(self):
        for state in STATUSES:
            self.assertEqual(normalize_tracker_row({**ROW,'Status':state})['Status'],state)

    def test_backup_contains_no_resume(self):
        payload=export_workspace_json([ROW],['0'*32],True)
        self.assertNotIn('resume_text',payload)
        self.assertNotIn('password',payload)


if __name__=='__main__':
    unittest.main()
