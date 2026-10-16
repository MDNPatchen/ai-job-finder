import unittest
from unittest.mock import patch
from coverage_health import coverage_messages,coverage_summary
from career_priority import order_for_review
from ranked_breakdowns import breakdowns_csv_rows
from mayo_source import fetch_mayo_jobs


def job(title,fit,detailed=True):
    return dict(title=title,company='Example',url='https://example.org/'+title,
        description='Lead operations and manage budgets. '*30,
        description_source='Employer posting details as supplied by provider' if detailed else 'RSS summary only',
        qualification_match={'fit_index':fit,'resume_present':True})

class ReviewReliabilityTests(unittest.TestCase):
    def test_coverage_distinguishes_limits_and_failure(self):
        rows=[dict(board='Mayo',bounded_coverage=True,status='Active'),
              dict(board='Capped',truncated=True,status='Partial'),
              dict(board='Broken',status='Failed'),
              dict(board='Details',status='Partial',failed_details=2)]
        groups=coverage_summary(rows)
        self.assertEqual(groups,dict(bounded=['Mayo'],capped=['Capped'],failed=['Broken'],incomplete=['Details']))
        messages=coverage_messages(rows)
        self.assertEqual(sum(level=='warning' for level,_ in messages),2)
        self.assertFalse(any(level=='warning' and 'Mayo' in text for level,text in messages))

    def test_leadership_order_does_not_inflate_fit_or_drop_jobs(self):
        jobs=[job('Workplace Experience Supervisor',92),job('Vice President Operations',90),
              job('Store Manager',90),job('Director of Partnerships',94)]
        result=order_for_review(jobs,'Leadership priorities')
        self.assertEqual([x['title'] for x in result[:2]],['Director of Partnerships','Vice President Operations'])
        self.assertEqual(len(result),len(jobs))
        self.assertEqual(result[1]['qualification_match']['fit_index'],90)
        self.assertNotIn('review_order',jobs[0])
        strict=order_for_review(jobs,'Highest fit index')
        self.assertEqual([x['qualification_match']['fit_index'] for x in strict],[94,92,90,90])

    def test_incomplete_evidence_reduces_priority_not_fit(self):
        jobs=[job('Director of Operations',94,False),job('Director of Partnerships',85)]
        result=order_for_review(jobs,'Leadership priorities')
        self.assertEqual(result[0]['title'],'Director of Partnerships')
        csv=breakdowns_csv_rows(result)
        self.assertEqual(csv[1]['Comparative fit index (0-96; not hiring probability)'],94)
        self.assertEqual(csv[1]['Review order'],'Leadership priorities')

    def test_empty_coverage_no_alert(self):
        self.assertEqual(coverage_messages([]),[])

    def test_mayo_keyword_scope_is_not_a_retrieval_failure(self):
        from test_mayo_source import LISTING,DETAIL
        result=fetch_mayo_jobs(lambda url: LISTING if '/search-jobs?' in url else DETAIL)
        self.assertTrue(result.diagnostics['bounded_coverage'])
        self.assertFalse(result.diagnostics['truncated'])
        capped=fetch_mayo_jobs(lambda url: LISTING if '/search-jobs?' in url else DETAIL,max_details=1)
        self.assertTrue(capped.diagnostics['truncated'])

    def test_populated_page_and_order_switch(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file('scripts/browser_fixture.py').run()
        app.radio(key='top_navigation').set_value('Find Jobs').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='review_order').value,'Leadership priorities')
        app.selectbox(key='review_order').set_value('Highest fit index').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Fit is provisional' in c.value for c in app.caption))
        self.assertFalse(app.warning)
