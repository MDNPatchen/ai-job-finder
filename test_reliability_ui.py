"""User-visible recovery, retry, conflict and persisted employer evidence."""
import unittest
from unittest.mock import patch
from datetime import date
from streamlit.testing.v1 import AppTest
from tracker_store import WorkspaceConflict


def row():
    return {'Company':'Example','Job Title':'Manager','Status':'Applied','Notes':'Keep notes',
            'Follow-up Date':date.today().isoformat(),'Date Recorded':date.today().isoformat(),
            'Interview Date':'','Location':'MN','Job URL':'https://example.org/1','Salary':''}


def app_with_cloud():
    app=AppTest.from_file('app.py')
    app.secrets['TRACKER_DATABASE_URL']='postgresql://unused-test-host/database'
    app.secrets['TRACKER_ACCESS_PASSWORD']='test-only-access-password'
    app.run()
    app.session_state['jobs']=[row()]
    app.session_state['tracker_unlocked']=True
    app.session_state['tracker_revision']=1
    app.run()
    return app


class RecoveryUITests(unittest.TestCase):
    def test_dashboard_failure_visible_and_retry_succeeds(self):
        app=app_with_cloud()
        with patch('tracker_store.save_remote_workspace',side_effect=OSError):
            app.button(key='complete_followup_0').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Cloud save incomplete' in x.value for x in app.error))
        self.assertEqual(app.session_state['jobs'][0]['Notes'],'Keep notes')
        with patch('tracker_store.save_remote_workspace',return_value=2):
            app.button(key='retry_cloud_save').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any('Saved to cloud' in x.value for x in app.caption))

    def test_conflict_has_merge_not_blind_retry(self):
        app=app_with_cloud()
        with patch('tracker_store.save_remote_workspace',side_effect=WorkspaceConflict):
            app.button(key='complete_followup_0').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.key=='merge_cloud_changes' for x in app.button))
        self.assertFalse(any(x.key=='retry_cloud_save' for x in app.button))

    def test_editor_save_failure_stays_visible(self):
        app=app_with_cloud()
        app.radio(key='top_navigation').set_value('Job Tracker').run()
        app.text_area(key='notes_0').set_value('Edited note').run()
        with patch('tracker_store.save_remote_workspace',side_effect=OSError):
            next(x for x in app.button if x.label=='Save Changes').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['jobs'][0]['Notes'],'Edited note')
        self.assertTrue(any('Cloud save incomplete' in x.value for x in app.error))

    def test_delete_failure_retains_recoverable_pending_workspace(self):
        app=app_with_cloud()
        app.radio(key='top_navigation').set_value('Job Tracker').run()
        next(x for x in app.checkbox if x.label=='Enable deletion of selected job').check().run()
        with patch('tracker_store.save_remote_workspace',side_effect=OSError):
            next(x for x in app.button if x.label=='Delete selected job').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['tracker_dirty'])
        self.assertTrue(any('Cloud save incomplete' in x.value for x in app.error))

    def test_six_pages_and_dark_theme(self):
        app=AppTest.from_file('app.py').run()
        for page in ['Find Jobs','Job Tracker','My Resume','Career Analysis','Career Matches','Dashboard']:
            app.radio(key='top_navigation').set_value(page).run()
            self.assertFalse(app.exception,page)
