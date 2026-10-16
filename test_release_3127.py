"""Search review partition and actionable tracker regressions."""
import unittest
from datetime import date
from career_priority import career_review_category, has_detailed_description
from tracker_store import upcoming_followups, complete_followup, export_workspace_json, import_workspace_json

class ReleaseTests(unittest.TestCase):
    def test_every_tier_has_one_category(self):
        titles=['Publisher','Director','Deputy Director','Unknown title','Manager','Specialist']
        expected=['Director / executive / publisher']*2+['Management / related roles']*3+['Other roles']
        self.assertEqual([career_review_category(t) for t in titles],expected)

    def test_missing_provenance_is_not_detailed(self):
        for source in [None,'','Provider RSS text — completeness not verified','RSS summary only — important requirements may be missing']:
            self.assertFalse(has_detailed_description({'description_source':source}))
        for source in ['Official full public job bulletin','Employer posting details as supplied by provider']:
            self.assertTrue(has_detailed_description({'description_source':source,'description':'Lead teams and manage budgets. '*20}))

    def test_due_window_and_closed_jobs(self):
        jobs=[{'Status':s,'Follow-up Date':d} for s,d in [
            ('Applied','2026-10-01'),('Interviewing','2026-10-16'),('Offer','2026-10-23'),
            ('Saved','2026-10-24'),('Rejected','2026-10-15'),('Withdrawn','2026-10-15'),
            ('Skipped','2026-10-15'),('Applied','invalid'),('Saved','')]]
        self.assertEqual([i for _,i,_ in upcoming_followups(jobs,date(2026,10,16))],[0,1,2])

    def test_complete_duplicate_title_only_updates_selected_row_and_backup(self):
        row={'Company':'Example','Job Title':'Manager','Status':'Applied','Notes':'Call recruiter','Follow-up Date':'2026-10-16'}
        jobs=[dict(row),dict(row)]
        complete_followup(jobs,1)
        restored=import_workspace_json(export_workspace_json(jobs,[],False).encode())['jobs']
        self.assertEqual(restored[0]['Follow-up Date'],'2026-10-16')
        self.assertEqual(restored[1]['Follow-up Date'],'')
        self.assertEqual(restored[1]['Notes'],'Call recruiter')
        self.assertEqual(restored[1]['Status'],'Applied')
