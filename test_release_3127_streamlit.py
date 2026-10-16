"""Offline Streamlit interactions for v3.1.27."""
import unittest
from datetime import date
from streamlit.testing.v1 import AppTest
from build_info import MATCHING_ENGINE_VERSION

class StreamlitReleaseTests(unittest.TestCase):
    def test_review_categories_and_description_filter(self):
        app=AppTest.from_file('app.py').run(timeout=60)
        app.radio(key='top_navigation').set_value('Find Jobs').run()
        base=dict(company='Example',government=False,location='MN',date='2026-10-16',source='Greenhouse',work_style='On-site',description='Lead operations and manage budgets. '*20)
        app.session_state['search_results']=[dict(base,title='Deputy Director',url='https://example.org/1',description_source='Official full public job bulletin'),dict(base,title='Specialist',url='https://example.org/2')]
        app.session_state['search_stats']=dict(run_id='20261016T214938Z',matching_version=MATCHING_ENGINE_VERSION,searched='2026-10-16',excluded=dict(old=0,undated=0,location=0),sources={},errors=[],fetched=2,preferences={})
        app.run()
        app.selectbox(key='career_review_filter').set_value('Management / related roles').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('1 results' in c.value for c in app.caption))
        app.selectbox(key='career_review_filter').set_value('All career levels').run()
        app.checkbox(key='full_description_filter').check().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('1 results' in c.value for c in app.caption))

    def test_complete_dashboard_reminder(self):
        app=AppTest.from_file('app.py').run(timeout=60)
        app.session_state['jobs']=[dict(Company='Test',**{'Job Title':'Manager','Status':'Applied','Notes':'Keep notes','Follow-up Date':str(date.today()),'Date Recorded':str(date.today()),'Interview Date':'','Location':'MN','Job URL':'https://example.org/1','Salary':''})]
        app.run()
        app.button(key='complete_followup_0').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['jobs'][0]['Follow-up Date'],'')
        self.assertEqual(app.session_state['jobs'][0]['Notes'],'Keep notes')
