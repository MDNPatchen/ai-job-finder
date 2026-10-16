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
