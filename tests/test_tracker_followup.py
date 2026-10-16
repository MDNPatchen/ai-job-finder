"""Tracker follow-up date storage and legacy backup compatibility."""
import unittest
from tracker_store import normalize_tracker_row, export_tracker_csv, import_tracker_csv

class TrackerFollowupTests(unittest.TestCase):
    def test_followup_roundtrip(self):
        job={'Company':'Example','Job Title':'Publisher','Status':'Applied','Follow-up Date':'2026-11-01'}
        output=import_tracker_csv(export_tracker_csv([job]).encode())
        self.assertEqual(output[0]['Follow-up Date'],'2026-11-01')

    def test_legacy_backup_imports(self):
        columns=['Company','Job Title','Location','Job URL','Salary','Status','Date Recorded','Interview Date','Notes']
        import csv,io
        stream=io.StringIO()
        writer=csv.DictWriter(stream,fieldnames=columns)
        writer.writeheader()
        writer.writerow({'Company':'Example','Job Title':'Publisher','Status':'Saved'})
        rows=import_tracker_csv(stream.getvalue().encode())
        self.assertEqual(rows[0]['Follow-up Date'],'')

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            normalize_tracker_row({'Company':'Example','Job Title':'Publisher','Status':'Saved','Follow-up Date':'tomorrow'})
