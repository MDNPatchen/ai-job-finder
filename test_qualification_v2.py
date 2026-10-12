"""Offline regression cases based on *types* of errors observed in a real search.

All examples are synthetic: no user resume or private job export is committed.
"""
import unittest

from qualification_v2 import (
    extract_requirements, assess_specialized_experience, role_alignment, recalibrate_match)
from qualification_matcher import assess_job_qualifications, compile_resume_profile
from ranked_breakdowns import evidence_index, evidence_sort_key


RESUME = (
    'Publisher & Operations Director with 25 years of management experience.\n'
    'Directed multiple regional publications and supervised managers.\n'
    'Oversee large divisional budgets, financial reports, forecasting and P&L.\n'
    'Negotiated vendors and reorganized distribution logistics.\n'
    'Led digital marketing, community partnerships, and strategic planning.\n'
)


def qualified(job):
    p=compile_resume_profile(RESUME,())
    return assess_job_qualifications(job,p,RESUME)


class QualificationV2Tests(unittest.TestCase):
    def test_transit_specific_requirements_must_lower_coo_fit(self):
        transit={'title':'Chief Operating Officer (Assistant Director of Transportation)',
                 'description':(
                    'Six years progressively responsible experience in the operational '
                    'management and strategic direction of a public transportation '
                    'organization providing oversight of total fleet operations. '
                    'Must possess and maintain a valid Florida Driver\'s License. '
                    'Requires a Bachelor\'s degree in transportation or business. '
                    'Responsibilities: budgeting, financial operations, leadership, '
                    'strategic planning, distribution, vendors and stakeholder engagement.')}
        generic={'title':'Chief Operating Officer',
                 'description':'Financial budgets, operations management, distribution, '
                               'strategic planning, vendors and partnerships.'}
        a,b=qualified(transit),qualified(generic)
        self.assertLess(evidence_index(a),evidence_index(b))
        self.assertLess(evidence_index(a),96)
        self.assertTrue(any('transit' in x['area'].lower()
                            for x in a['specialized_requirements']))
        self.assertTrue(any(x['type']=='License / certification'
                            for x in a['screeners']))
        self.assertTrue(any(x['type']=='Education'
                            for x in a['screeners']))
        self.assertTrue(any(x['type']=='Experience duration'
                            for x in a['screeners']))

    def test_nyc_civil_service_requirement_is_caution_not_exclusion(self):
        j={'title':'Commissary Operations Manager',
           'description':(
                'ONLY APPLICANTS MUST BE PERMANENT IN THE TITLE STAFF ANALYST. '
                'Work with correctional facilities and commissary vendors. '
                'Coordinate logistics, operational data and inventory reports.')}
        result=qualified(j)
        self.assertTrue(any(x['type']=='Civil-service eligibility'
                            for x in result['screeners']))
        self.assertTrue(result['cautions'])
        self.assertLess(evidence_index(result),75)
        self.assertNotIn('ineligible',str(result).lower())

    def test_product_marketing_experience_is_not_equivalent_to_any_career_years(self):
        j={'title':'Product Marketing Manager',
           'description':'Requires 5+ years of experience in product marketing, '
                         'go-to-market commercialization and product launches. '
                         'Coordinate stakeholders and reporting dashboards.'}
        result=qualified(j)
        self.assertTrue(any(x['area']=='Product marketing / go-to-market'
                            and x['needs_verification']
                            for x in result['specialized_requirements']))
        self.assertTrue(any('specific field' in x['resume_status']
                            for x in result['screeners']
                            if x['type']=='Experience duration'))
        self.assertLess(evidence_index(result),85)

    def test_restaurant_manager_not_equated_with_newspaper_publisher(self):
        j={'title':'General Manager (Taco Bell)',
           'description':'Requires 3-5 years of restaurant management experience, '
                         'food safety, inventory management, budgeting and staff training.'}
        q=qualified(j)
        self.assertLess(evidence_index(q),70)
        self.assertTrue(any(x['area']=='Restaurant / food-service management'
                            for x in q['specialized_requirements']))

    def test_operations_director_clearly_relevant_without_domain_requirement(self):
        j={'title':'Director of Operations',
           'description':'Oversee regional operations, manage managers, track budgets, '
                         'renegotiate vendors, improve operational efficiency and KPIs.'}
        q=qualified(j)
        self.assertGreater(evidence_index(q),70)
        self.assertFalse(q['specialized_requirements'])

    def test_no_false_nurse_license_from_a_recommended_jobs_sidebar(self):
        j={'title':'Project Manager',
           'description':'Responsibilities: program management and budgets. '
                         'Similar Jobs: Registered Nurse - ICU - RN, Nurse Practitioner.'}
        q=qualified(j)
        self.assertFalse(any(x['type']=='License / certification'
                             for x in q['screeners']))

    def test_explicit_rn_license_is_not_hidden(self):
        q=qualified({'title':'Hospital Operations Director',
                     'description':'Current RN license required and healthcare administration experience.'})
        self.assertTrue(any(x['type']=='License / certification'
                            for x in q['screeners']))

    def test_general_years_does_not_claim_specialized_experience(self):
        s=extract_requirements('Six years of public transit operational management experience required.',RESUME)
        rows=[x for x in s if x['type']=='Experience duration']
        self.assertTrue(rows)
        self.assertIn('specific field',rows[0]['resume_status'])

    def test_corporate_age_is_not_recast_as_required_experience(self):
        self.assertFalse(any(x['type']=='Experience duration' for x in
            extract_requirements('Our company celebrated 25 years in business.',RESUME)))

    def test_match_sort_orders_director_above_specialized_manager(self):
        strong=qualified({'title':'Director of Operations',
                          'description':'Operational management, budgets, distribution and strategic planning.'})
        niche=qualified({'title':'General Manager (Dunkin Donuts)',
                         'description':'Required 3 years in restaurant management. '
                                       'Control budgets and customer service.'})
        self.assertLess(
            evidence_sort_key({'title':'Director of Operations','date':'2026-10-11',
                               'rank':12,'qualification_match':strong}),
            evidence_sort_key({'title':'General Manager (Dunkin Donuts)','date':'2026-10-11',
                               'rank':15,'qualification_match':niche}))

    def test_sparse_description_warns_about_missing_requirements(self):
        q=qualified({'title':'Director of Operations','description':'Operations management.'})
        self.assertIn('Limited details',q['description_completeness'])

    def test_no_resume_has_zero_qualification_fit(self):
        q=assess_job_qualifications({'title':'Director of Operations',
                                    'description':'Manage company operations.'},
                                   compile_resume_profile('',()),'')
        self.assertEqual(evidence_index(q),0)

if __name__=='__main__':
    unittest.main()
