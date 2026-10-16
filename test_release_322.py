import csv,tempfile,unittest
from pathlib import Path
from career_priority import leadership_tier,order_for_review,review_priority_details
from ranked_breakdowns import breakdowns_csv_rows
from export_audit import audit_csv,FIT,PRIORITY
from test_release_321 import job

class ExportReliabilityTests(unittest.TestCase):
    def audit(self,rows):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'export.csv'
            with path.open('w',newline='',encoding='utf-8-sig') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            return audit_csv(path)
    def rows(self):
        return breakdowns_csv_rows(order_for_review([job('Executive Assistant to the President',95),job('Director of Operations',90)],'Leadership priorities'),'3.2.2','20261016T224118Z')
    def test_support_roles_do_not_inherit_executive_titles(self):
        for title in ['Executive Assistant to the President','Assistant to the Director','CEO’s Assistant']:
            self.assertEqual(leadership_tier(title),0,title)
        self.assertEqual(leadership_tier('Assistant General Manager'),1)
        self.assertEqual(leadership_tier('Chief Executive Officer'),4)
        self.assertEqual(leadership_tier('Deputy County Manager'),4)
    def test_export_priority_reconciles_and_preserves_fit(self):
        rows=self.rows()
        self.assertEqual(rows[0]['Job title'],'Director of Operations')
        self.assertEqual(rows[1][FIT],95)
        self.assertEqual(rows[1][PRIORITY],77)
        self.assertTrue(self.audit(rows)['passed'])
    def test_wrong_order_and_duplicates_fail(self):
        rows=self.rows();rows.reverse()
        self.assertFalse(self.audit(rows)['passed'])
        rows=self.rows();rows[1]['Job URL']=rows[0]['Job URL']
        self.assertFalse(self.audit(rows)['passed'])
    def test_nonfinite_and_incorrect_adjustments_fail(self):
        for value in ['NaN','inf','bad',97,-1]:
            rows=self.rows();rows[0][FIT]=value
            self.assertFalse(self.audit(rows)['passed'])
        rows=self.rows();rows[0][PRIORITY]=99
        self.assertFalse(self.audit(rows)['passed'])
    def test_older_export_is_unverified_not_falsely_passed(self):
        rows=self.rows()
        for row in rows:
            for key in [PRIORITY,'Role-level review adjustment','Description review adjustment']:row.pop(key)
        result=self.audit(rows)
        self.assertFalse(result['passed'])
        self.assertTrue(any(f['status']=='unverified' for f in result['findings']))
    def test_invalid_fit_does_not_break_review_priority(self):
        for value in ['bad',float('nan'),float('inf'),None]:
            self.assertTrue(review_priority_details(job('Director',value))['priority']<=0)

class SpecialtyEvidenceTests(unittest.TestCase):
    def test_missing_specialties_are_flagged_and_counted_once(self):
        from test_career_fit_guardrails import fitted,GENERIC_DUTIES
        for title,requirements,field in [
            ('Payroll Director','Required experience in payroll systems and time capture systems.','Payroll'),
            ('Senior Director, Revenue Cycle','Minimum 8 years of experience in revenue cycle management required.','revenue cycle'),
            ('Director, Payments Performance - Product','10+ years of deep payments experience on the merchant acceptance side.','payments')]:
            q=fitted(title,GENERIC_DUTIES+requirements)
            self.assertTrue(any(field.lower() in x['area'].lower() for x in q['career_fit_cautions']),title)
            self.assertTrue(q['specialized_requirements'],title)
            self.assertGreater(q['ranking_overlap_relief'],0,title)
            self.assertLess(q['fit_index'],fitted('Director of Operations')['fit_index'])
    def test_positive_specialty_evidence_removes_title_caution(self):
        from career_fit_guardrails import evaluate_career_fit
        for title,resume in [
            ('Payroll Director','Managed payroll processing and payroll tax compliance.'),
            ('Director of Revenue Cycle','Led revenue cycle operations and patient billing.'),
            ('Director of Payments Performance','Led merchant acquiring and payment processing.')]:
            self.assertEqual(evaluate_career_fit({'title':title},resume)['penalty'],0)
    def test_negation_and_generic_finance_do_not_supply_specialty(self):
        from test_career_fit_guardrails import fitted,RESUME,GENERIC_DUTIES
        for title,specialty in [('Payroll Director','payroll administration'),('Revenue Cycle Director','revenue cycle'),('Director of Payments Performance','payments processing')]:
            q=fitted(title,GENERIC_DUTIES,RESUME+' No experience in '+specialty+'.')
            self.assertTrue(q['career_fit_cautions'])
    def test_general_operations_not_penalized_for_vendor_payments(self):
        from career_fit_guardrails import evaluate_career_fit
        from qualification_domains import identify_specialized_requirements
        j={'title':'Director of Operations','description':'Manage vendor payments, budgeting and revenue growth.'}
        self.assertEqual(evaluate_career_fit(j,'Managed vendor payments and budgeting.')['penalty'],0)
        self.assertFalse(identify_specialized_requirements(j,''))
    def test_preferred_payroll_experience_not_called_required(self):
        from qualification_domains import identify_specialized_requirements
        findings=identify_specialized_requirements({'title':'Payroll Director','description':'Payroll systems experience preferred.'},'')
        self.assertEqual(findings[0]['priority'],'Preferred experience')

class EmployerExportTests(unittest.TestCase):
    def test_saved_evidence_is_exact_posting_scoped_and_dated(self):
        from datetime import datetime,timezone
        from employer_evidence import evidence_key,attach_saved_evidence
        a=dict(company='Example',source='Greenhouse',url='https://example.org/1')
        b=dict(a,url='https://example.org/2')
        checks={evidence_key(a):dict(checked_at='2026-10-16T12:00:00+00:00',identity={'status':'Exact-name legal entity match'},posting={'status':'Page responds','vacancy_status':'Open status not established'})}
        now=datetime(2026,10,16,13,tzinfo=timezone.utc)
        rows=breakdowns_csv_rows(attach_saved_evidence([a,b],checks,now))
        self.assertEqual(rows[0]['Employer check freshness'],'Current (within 24 hours)')
        self.assertEqual(rows[1]['Saved legal identity check'],'Not checked')
        self.assertEqual(rows[0]['Saved posting availability check'],'Open status not established')
        self.assertNotIn('employer_evidence_summary',a)
        stale=attach_saved_evidence([a],checks,datetime(2026,10,18,tzinfo=timezone.utc))[0]
        self.assertIn('Stale',stale['employer_evidence_summary']['freshness'])
    def test_future_or_undated_checks_never_claim_freshness(self):
        from datetime import datetime,timezone
        from employer_evidence import evidence_key,attach_saved_evidence
        a=dict(company='Example',source='Board',url='https://example.org/1')
        for date in ['bad','2027-01-01T00:00:00+00:00','2026-10-16T12:00:00']:
            row=attach_saved_evidence([a],{evidence_key(a):{'checked_at':date}},datetime(2026,10,16,tzinfo=timezone.utc))[0]
            self.assertNotIn('Current',row['employer_evidence_summary']['freshness'])

class CompleteFeedTests(unittest.TestCase):
    def test_feed_larger_than_old_limit_is_complete(self):
        import io,xml.etree.ElementTree as ET
        from source_http import read_bounded
        body=b'<rss><channel><item><description>'+b'x'*3_500_000+b'</description></item></channel></rss>'
        received=read_bounded(io.BytesIO(body))
        self.assertEqual(len(received),len(body))
        self.assertEqual(len(ET.fromstring(received).findall('.//item')),1)
    def test_oversized_feed_has_size_error_not_fake_xml_error(self):
        import io
        from source_http import read_bounded
        self.assertEqual(read_bounded(io.BytesIO(b'1234'),limit=4),b'1234')
        with self.assertRaisesRegex(ValueError,'complete feed not retrieved'):
            read_bounded(io.BytesIO(b'12345'),limit=4)
    def test_deadline_applies_during_body_read(self):
        import io
        from source_http import read_bounded,request_budget
        with request_budget(-1):
            with self.assertRaises(TimeoutError):read_bounded(io.BytesIO(b'abc'))

class StreamingRSSReliabilityTests(unittest.TestCase):
    def test_large_feed_and_more_than_previous_item_caps(self):
        import io
        from source_rss import iter_rss_response
        body=b'<rss><channel>'+b'<item><title>Director</title><description>'+b'x'*3_100_000+b'</description></item>'+b'<item><title>Manager</title></item>'*750+b'</channel></rss>'
        titles=[x.findtext('title') for x in iter_rss_response(io.BytesIO(body))]
        self.assertEqual(len(titles),751)
        self.assertEqual(titles[0],'Director')
    def test_incomplete_document_is_not_successful(self):
        import io
        from source_rss import iter_rss_response
        with self.assertRaisesRegex(ValueError,'Malformed RSS'):
            list(iter_rss_response(io.BytesIO(b'<rss><channel><item><title>A</title></item>')))
    def test_provider_error_and_byte_limit_are_explicit(self):
        import io
        from source_rss import iter_rss_response
        with self.assertRaisesRegex(ValueError,'Unexpected RSS'):
            list(iter_rss_response(io.BytesIO(b'<error>unavailable</error>')))
        with self.assertRaisesRegex(ValueError,'complete feed not retrieved'):
            list(iter_rss_response(io.BytesIO(b'<rss>'+b' '*100+b'</rss>'),limit=50))
