"""Regression suite for actual private employer qualifications in escaped ATS HTML.

Every job and resume here is synthetic. The app compares *documented* evidence,
never decides whether someone is eligible or could learn the specialty.
"""
import unittest
from html import escape

from posting_requirements import extract_posting_requirements, _clean
from qualification_matcher import assess_job_qualifications, compile_resume_profile
from ranked_breakdowns import breakdowns_csv_rows, evidence_index
from career_fit_guardrails import evaluate_career_fit

RESUME=(
    'Group newspaper publisher and operations director with 25 years of '
    'management experience. Oversaw departmental leaders, budgets, P&L, '
    'revenue growth, marketing, vendor contracts, distribution and '
    'logistics for several publishing locations.'
)
DUTIES=('Lead regional business operations, people, budget forecasting, '
        'stakeholder communications, strategic planning, revenue growth, '
        'programs, negotiation and vendor contracts. '*8)


def html_job(title, requirements_heading, requirements, preferred='', intro=DUTIES):
    html=(
        '<div><h2>What You Will Do</h2><ul><li>'+intro+'</li></ul>'
        '<p><em><strong>'+requirements_heading+'</strong></em></p><ul>'
        '<li>'+requirements+'</li></ul>'
    )
    if preferred:
        html+='<h3>Nice to Have</h3><ul><li>'+preferred+'</li></ul>'
    html+='</div>'
    return {'title':title,'description':escape(html)}


def scored(job,resume=RESUME):
    cleaned={**job,'description':_clean(job.get('description'))}
    return assess_job_qualifications(cleaned,compile_resume_profile(resume,()),resume)


def flagged(job,resume=RESUME):
    return extract_posting_requirements(job,resume)


class PrivateEmployerMinimumTests(unittest.TestCase):
    def test_escaped_ats_html_retains_applicant_section_and_bullet(self):
        job=html_job('EHS Specialist','What You’ll Need',
                     '5+ years of environmental health and safety (EHS) '
                     'experience leading OSHA compliance programs.')
        plain=_clean(job['description'])
        self.assertIn('What You’ll Need',plain)
        self.assertIn('5+ years of environmental',plain)
        self.assertNotIn('<li>',plain)
        self.assertNotIn('&lt;',plain)
        item=flagged(job)
        ehs=next(x for x in item['checks'] if
                 x['area']=='Environmental health and safety / OSHA')
        self.assertTrue(ehs['priority'].startswith('Required'))
        self.assertGreater(ehs['ranking_caution'],0)

    def test_later_ehs_minimum_wins_over_earlier_mention_in_duties(self):
        job=html_job('EHS Specialist','What We Need From You',
                     '5 years of EHS experience with OSHA compliance.',
                     intro='Develop and deliver EHS training programs. '+DUTIES)
        ehs=next(x for x in flagged(job)['checks']
                 if x['area']=='Environmental health and safety / OSHA')
        self.assertTrue(ehs['priority'].startswith('Required'))
        self.assertIn('years',ehs['listing_excerpt'].lower())

    def test_product_design_eight_year_requirement_not_general_management(self):
        job=html_job('Manager, Product Design',"What you're great at:",
                     '8+ years of product design experience building UX '
                     'products and demonstrating Figma expertise.')
        minimums=flagged(job)
        rule=next(x for x in minimums['checks']
                  if x['area']=='Product / UX design portfolio')
        self.assertTrue(rule['priority'].startswith('Required'))
        self.assertGreater(rule['ranking_caution'],0)
        ranked=scored(job)
        general=scored({'title':'Business Operations Manager','description':DUTIES})
        self.assertLess(evidence_index(ranked),evidence_index(general))
        self.assertTrue(ranked['career_fit_cautions'])

    def test_compensation_equity_specific_experience_not_generic_budgeting(self):
        job=html_job('Manager, Compensation & Equity',"What you're great at:",
                     '7 years of experience leading compensation programs, '
                     'equity compensation administration and pay equity analysis.')
        found=flagged(job)['checks']
        self.assertTrue(any(x['area']=='Compensation and equity administration'
                            and x['ranking_caution']>0 for x in found))
        assessment=scored(job)
        self.assertGreater(assessment['posting_requirement_penalty'],0)
        self.assertTrue(any(item['ranking_caution']>0 for item in assessment['career_fit_cautions']))
        self.assertGreater(assessment['ranking_overlap_relief'],0)

    def test_mass_spec_scientist_not_business_management(self):
        job=html_job('Senior Scientist - Mass Spec Production (LC-MS/MS)',
                     'Qualifications & Skills',
                     '4 years experience with LC-MS/MS, mass spectrometry, '
                     'bioanalytical method development and chromatography.')
        q=scored(job)
        self.assertGreater(q['posting_requirement_penalty'],0)
        self.assertTrue(any(x['ranking_caution']>0 for x in q['career_fit_cautions']))
        self.assertGreater(q['ranking_overlap_relief'],0)
        self.assertLess(evidence_index(q),evidence_index(
            scored({'title':'Regional Operations Manager','description':DUTIES})))

    def test_information_technology_project_requirements(self):
        job=html_job('Senior IT Project Manager','What You’ll Bring',
                     '7+ years of IT project management and enterprise '
                     'software implementation projects, including systems integration.')
        q=scored(job)
        self.assertTrue(any(x['area']=='IT-specific project delivery'
                            and x['ranking_caution']>0
                            for x in q['posting_requirement_checks']))
        self.assertTrue(any(x['ranking_caution']>0 for x in q['career_fit_cautions']))
        self.assertGreater(q['ranking_overlap_relief'],0)

    def test_transfer_only_title_is_application_restriction(self):
        job={'title':'Accounting Coordinator (TRANSFER ONLY)',
             'description':DUTIES}
        q=scored(job)
        self.assertTrue(q['application_restricted'])
        self.assertGreaterEqual(q['posting_requirement_penalty'],45)
        csv=breakdowns_csv_rows([{
            **job,'company':'Example Community College','qualification_match':q
        }])[0]
        self.assertEqual(csv['Posting explicitly restricts to internal applicants'],
                         'Yes — verify eligibility')

    def test_transfer_only_description_applies_only_in_hiring_context(self):
        restricted=flagged({'title':'Accounting Coordinator',
            'description':'Applications accepted from current employees: transfers only.'})
        unconnected=flagged({'title':'Data Manager',
            'description':'This technical API supports file transfers only.'})
        self.assertTrue(restricted['application_restricted'])
        self.assertFalse(unconnected['application_restricted'])

    def test_nice_to_have_after_required_section_not_accidentally_required(self):
        job=html_job('Operations Manager','Qualifications & Skills',
                     '10 years leading operations teams and budgets.',
                     preferred='Experience in LC-MS/MS laboratory analysis preferred.')
        found=flagged(job)['checks']
        mass=next(x for x in found if
                  x['area']=='Analytical laboratory mass spectrometry')
        self.assertEqual(mass['ranking_caution'],0)
        self.assertEqual(mass['priority'],'Preferred / mentioned')

    def test_required_after_preferred_same_field_takes_precedence(self):
        desc=(
            '<h2>Desired Qualifications</h2><li>EHS experience preferred.</li>'
            '<h2>What You’ll Need</h2><li>4 years environmental health and '
            'safety experience managing OSHA compliance.</li>')
        result=flagged({'title':'Operations Manager','description':desc})
        ehs=next(x for x in result['checks']
                 if x['area']=='Environmental health and safety / OSHA')
        self.assertTrue(ehs['priority'].startswith('Required'))
        self.assertGreater(ehs['ranking_caution'],0)

    def test_specialist_keywords_in_responsibilities_are_not_mandatory(self):
        job=html_job('Business Operations Manager','What You’ll Need',
                     'Budget management and stakeholder engagement.',
                     intro='Coordinate with product design and environmental '
                           'health and safety groups; track specialist reports. '+DUTIES)
        found=flagged(job)
        self.assertFalse(any(x['ranking_caution'] for x in found['checks']))
        self.assertEqual(evaluate_career_fit(
            {'title':job['title'],'description':job['description']},RESUME)['penalty'],0)

    def test_specialist_resume_evidence_avoids_unwarranted_caution(self):
        job=html_job('Manager, Compensation & Equity',"What you're great at:",
                     '7 years of compensation programs and equity '
                     'compensation administration experience.')
        specialist_resume=RESUME+(
            ' Led compensation programs and equity compensation administration '
            'for 7 years across regional businesses.')
        q=scored(job,specialist_resume)
        self.assertEqual(q['career_fit_penalty'],0)
        self.assertEqual(q['posting_requirement_penalty'],0)

    def test_fulllength_ats_posting_preserves_late_qualification_section(self):
        desc=escape('<div><h2>What We Do</h2><p>'+DUTIES*7+
                    '</p><h3>What You Need</h3><li>'
                    '7+ years of experience in LC-MS/MS mass spectrometry.</li></div>')
        plain=_clean(desc)
        self.assertIn('7+ years',plain)
        found=flagged({'title':'Senior Scientist','description':desc})
        self.assertTrue(any(x['area']=='Analytical laboratory mass spectrometry'
                            and x['ranking_caution']>0 for x in found['checks']))


if __name__=='__main__':
    unittest.main()
