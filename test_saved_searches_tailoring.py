"""Saved searches (stored with the tracker) and per-job tailoring sheets."""
import unittest

import saved_searches as ss
from tailoring import build_sheet, missing_terms, sheet_text
from tracker_store import export_workspace_json, import_workspace_json
from workspace_merge import merge_profile

FILTERS = {'f_search': 'communications director', 'f_state': 'North Dakota (ND)', 'f_work': 'On-site + Hybrid',
           'f_include': ['MN — Minnesota', 'SD — South Dakota'], 'f_minsal': 90000, 'f_unknownpay': True}
OPTIONS = {'f_state': ['All states', 'North Dakota (ND)'], 'f_work': ['On-site + Hybrid', 'Hybrid only'],
           'f_include': ['MN — Minnesota', 'SD — South Dakota']}


class SavedSearchTests(unittest.TestCase):
    def test_upsert_replaces_by_name_and_keeps_newest_first(self):
        items = ss.upsert([], 'Comms Upper Midwest', FILTERS)
        items = ss.upsert(items, 'Nonprofit ED', {'f_search': 'executive director'})
        items = ss.upsert(items, 'comms upper midwest', {**FILTERS, 'f_minsal': 100000})
        self.assertEqual([x['name'] for x in items], ['comms upper midwest', 'Nonprofit ED'])
        self.assertEqual(items[0]['filters']['f_minsal'], 100000)
        self.assertEqual(ss.remove(items, 'NONPROFIT ED')[0]['name'], 'comms upper midwest')

    def test_name_required(self):
        with self.assertRaises(ValueError):
            ss.upsert([], '   ', FILTERS)

    def test_malformed_entries_dropped(self):
        items = ss.clean_saved_searches([
            {'name': 'Good', 'filters': {'f_search': 'x', 'f_minsal': -5, 'f_unknownpay': 'yes', 'bogus': 1}},
            {'name': '', 'filters': {'f_search': 'y'}}, 'junk', {'name': 'Empty', 'filters': {}}])
        self.assertEqual(items, [{'name': 'Good', 'filters': {'f_search': 'x', 'f_minsal': 0}}])
        self.assertEqual(len(ss.clean_saved_searches([{'name': f'S{i}', 'filters': {'f_search': 'x'}}
                                                      for i in range(40)])), ss.MAX_SEARCHES)

    def test_capture_and_apply_respect_current_options(self):
        state = {**FILTERS, 'unrelated': 1}
        captured = ss.capture(state)
        self.assertNotIn('unrelated', captured)
        target = {}
        ss.apply(target, {**captured, 'f_state': 'Atlantis (AT)', 'f_include': ['MN — Minnesota', 'XX — Gone']},
                 OPTIONS)
        self.assertNotIn('f_state', target)                    # option no longer offered
        self.assertEqual(target['f_include'], ['MN — Minnesota'])
        self.assertEqual(target['f_search'], 'communications director')

    def test_saved_searches_round_trip_and_merge(self):
        searches = ss.upsert([], 'Comms', FILTERS)
        raw = export_workspace_json([], [], False, {}, {'answers': {'pnl': 'Yes'}, 'saved_searches': searches})
        self.assertEqual(import_workspace_json(raw.encode())['profile']['saved_searches'], searches)
        merged = merge_profile({}, {'answers': {}}, {'saved_searches': searches})
        self.assertEqual(merged['saved_searches'], searches)    # fresh session takes the saved list


JOB_TEXT = ('Lead the communications team. Partner with stakeholders across the health system. '
            'Internal communications and executive communications support the health system. '
            'Requires a bachelor degree. Sanford Health offers dental and vision insurance.')


class TailoringTests(unittest.TestCase):
    def test_missing_terms_stay_within_clauses_and_skip_employer(self):
        terms = missing_terms(JOB_TEXT, 'Served as spokesperson. Managed budgets.', 'Sanford Health')
        self.assertIn('health system', terms)
        self.assertNotIn('communications executive', terms)     # spans "communications. Partner" no
        self.assertNotIn('sanford', ' '.join(terms))
        self.assertNotIn('insurance', terms)

    def test_terms_already_in_resume_are_not_suggested(self):
        terms = missing_terms(JOB_TEXT, 'Built communications plans for the health system.', '')
        self.assertNotIn('health system', terms)
        self.assertNotIn('communications', terms)

    def test_sheet_orders_by_field_and_lists_every_part(self):
        job = {'title': 'Director of Communications', 'company': 'Sanford Health', 'url': 'https://example.org/1',
               'description': JOB_TEXT, 'qualification_match': {
                   'resume_matches': [
                       {'area': 'Financial & P&L leadership', 'match_origin': 'Job description',
                        'resume_evidence': ['Managed budgets.'], 'listing_excerpt': 'budget'},
                       {'area': 'Communications & public relations', 'match_origin': 'Job description',
                        'resume_evidence': ['Served as spokesperson.'], 'listing_excerpt': 'communications'},
                       {'area': 'Operations leadership', 'match_origin': 'Job title only',
                        'resume_evidence': ['x'], 'listing_excerpt': 'x'}],
                   'confirmed_only': [{'area': 'Revenue growth & transformation'}],
                   'not_documented': [{'area': 'Healthcare administration'}],
                   'screeners': [{'type': 'Education', 'listing_excerpt': 'Requires a bachelor degree.',
                                  'resume_status': 'Verify'}]}}
        sheet = build_sheet(job, 'Served as spokesperson. Managed budgets.')
        self.assertEqual(sheet['family'], 'Communications & public affairs')
        self.assertEqual([x['area'] for x in sheet['lead_with']],
                         ['Communications & public relations', 'Financial & P&L leadership'])
        self.assertEqual(sheet['add_to_resume'], ['Revenue growth & transformation'])
        self.assertEqual(sheet['gaps'], ['Healthcare administration'])
        text = sheet_text(sheet)
        for heading in ('LEAD WITH', 'YOU CONFIRMED THESE', 'WORDS THEY REPEAT', 'GAPS TO ADDRESS',
                        'REQUIREMENTS TO CHECK'):
            self.assertIn(heading, text)
        self.assertIn('Your resume: Served as spokesperson.', text)


if __name__ == '__main__':
    unittest.main()


class InAppTests(unittest.TestCase):
    """Drive the real page with the offline fixture (needs Streamlit; runs in CI)."""
    @classmethod
    def setUpClass(cls):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError as exc:
            raise unittest.SkipTest(str(exc))
        cls.AppTest = AppTest

    def find_jobs(self):
        app = self.AppTest.from_file('scripts/browser_fixture.py').run()
        app.radio(key='top_navigation').set_value('Find Jobs').run()
        self.assertFalse(app.exception)
        return app

    def test_save_search_from_the_form(self):
        app = self.find_jobs()
        app.text_input(key='f_search').input('communications director')
        app.text_input(key='f_save_name').input('Comms nationwide')
        next(b for b in app.button if b.label == 'Save this search').click().run()
        self.assertFalse(app.exception)
        saved = app.session_state['saved_searches']
        self.assertEqual(saved[0]['name'], 'Comms nationwide')
        self.assertEqual(saved[0]['filters']['f_search'], 'communications director')
        self.assertEqual(app.selectbox(key='saved_search_pick').value, 'Comms nationwide')
        self.assertFalse(app.warning)

    def test_tailoring_sheet_on_cards(self):
        app = self.find_jobs()
        self.assertTrue(any(e.label == 'Tailoring sheet' for e in app.expander))
        self.assertTrue(any('Lead with' in m.value for m in app.markdown))
