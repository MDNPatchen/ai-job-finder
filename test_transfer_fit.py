"""Regression tests: skills must outweigh senior-sounding titles.

All resumes/jobs below are synthetic; no private resume or application data
is included in the public repository.
"""
import ast
import re
import unittest
from pathlib import Path

from qualification_matcher import compile_resume_profile, assess_job_qualifications
from ranked_breakdowns import evidence_index
from transfer_fit import transfer_fit, supported_transfer_areas

SAMPLE_RESUME = (
    'Regional Business Manager\n'
    'Managed several locations and supervised managers and employees.\n'
    'Responsible for P&L, annual budgets and forecasts.\n'
    'Improved operational performance, distribution logistics, and workflows.\n'
    'Negotiated vendor contracts, led strategic planning and revenue growth.\n'
    'Built community partnerships and marketing strategy.\n'
)


def qualified(title, description):
    profile=compile_resume_profile(SAMPLE_RESUME,())
    return assess_job_qualifications(
        {'title':title,'description':description},profile,SAMPLE_RESUME)


class TransferabilityTests(unittest.TestCase):
    def test_job_duties_outrank_impressive_title(self):
        transferable=qualified('Vendor Relations Lead',
            'Lead vendor and contract negotiations, oversee budgets and '
            'operational improvement, manage staff and strategic planning. '
            'Collaborate with regional teams and community partnerships. '
            'Track revenue performance and improve workflows across locations. '
            'Experience working across departments and teams is valuable.')
        thin=qualified('Vice President of Operations',
            'Oversee vendor contracts. Specialized doctoral research '
            'background and deep laboratory technical experience required. '
            'Design academic laboratory experiments and scientific studies. '
            'Direct bench research processes and publish scientific findings.')
        self.assertGreater(evidence_index(transferable),evidence_index(thin))
        self.assertTrue(any(x['area']=='Negotiation & vendor management'
                            for x in transferable['transferable_strengths']))

    def test_title_only_keyword_is_discounted(self):
        def entry(name, origin='Job description'):
            return {'area':name,'match_origin':origin,
                    'listing_excerpt':'operations responsibilities',
                    'resume_evidence':['Led business operations']}
        areas=['Operations leadership','Financial & P&L leadership',
               'Talent & organizational change','Strategic planning & execution']
        base={'resume_present':True,
              'resume_matches':[entry(x) for x in areas],
              'confirmed_only':[], 'not_documented':[]}
        job={'title':'Director of Operations',
             'description':'Manage company finances and business operations. '*20}
        duties=transfer_fit(base,job,48)
        title_only=transfer_fit({**base,'resume_matches':[
            entry(x,'Job title only') for x in areas]},job,97)
        self.assertGreater(duties['index'], title_only['index'])
        self.assertTrue(duties['transferable_strengths'])
        self.assertFalse(title_only['transferable_strengths'])

    def test_confirmed_only_is_not_mistaken_for_resume_evidence(self):
        info={'resume_present':True,'resume_matches':[],
              'confirmed_only':[{'area':'Multi-site business leadership',
                                 'match_origin':'Job description'}],
              'not_documented':[]}
        out=transfer_fit(info,{'description':'Manage a multi-site business. '*20},70)
        self.assertTrue(out['transferable_strengths'])
        self.assertEqual(out['transferable_strengths'][0]['evidence'],
                         'Confirmed separately; add résumé evidence')
        self.assertLess(out['index'],40)

    def test_required_specialized_field_low_priority_without_proof(self):
        q=qualified('Regional Logistics Program Lead',
                    'Responsible for regional operations, budgets, vendor '
                    'negotiations and supervising teams. Strategic planning '
                    'and workforce leadership are essential. '*8)
        good=transfer_fit(q,{'description':'Maintain regional operations. '*25},60)
        specialized=transfer_fit(q,{'description':'Maintain regional operations. '*25},
                                 98, specialty_penalty=23, credential_penalty=11)
        self.assertLess(specialized['index'],good['index'])

    def test_bare_listing_does_not_get_near_perfect_fit(self):
        q=qualified('Director of Operations','Budget management.')
        self.assertLessEqual(evidence_index(q),74)

    def test_job_title_and_description_match_sources_separated(self):
        q=qualified('Operations Director',
                    'Lead strategic planning and negotiate vendor contracts. '
                    'Handle all annual budgets and team development.')
        ops=[i for i in q['resume_matches'] if i['area']=='Operations leadership']
        self.assertEqual(ops[0]['match_origin'],'Job title only')
        self.assertTrue(any(i['match_origin']=='Job description'
                            for i in q['resume_matches']))
        self.assertFalse(any(i['area']=='Operations leadership'
                             for i in supported_transfer_areas(q)))

    def test_nontraditional_job_title_can_qualify_by_actual_duties(self):
        source=Path(__file__).with_name('app.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        func=next(x for x in tree.body if isinstance(x,ast.FunctionDef)
                  and x.name=='score_job')
        env={
            're':re,
            'role_classification':lambda title:None,
            'SPECIALIST_EXCLUSIONS':re.compile('engineering director|nurse|physician',re.I),
            'compile_resume_profile':compile_resume_profile,
            'verified_competencies':lambda:set(),
            'assess_job_qualifications':assess_job_qualifications,
            'evidence_index':evidence_index,
            'states_in_location':lambda location:['MN'],
        }
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=[func],type_ignores=[])),'app.py','exec'),env)
        job={
            'title':'Partner Experience Lead',
            'description':('Manage teams and staff, operational improvement, '
                           'financial budgets, revenue growth, strategic planning, '
                           'distribution logistics and vendor contracts across '
                           'multiple locations. Build community partnerships and '
                           'deliver marketing campaigns. '*6),
            'government':False,
            'location':'Rochester, MN',
        }
        scored=env['score_job'](job,SAMPLE_RESUME)
        self.assertIsNotNone(scored)
        self.assertEqual(scored['category'],'Transferable-strength match')
        self.assertGreaterEqual(evidence_index(scored['qualification_match']),58)
        job['title']='Engineering Director'
        self.assertIsNone(env['score_job'](job,SAMPLE_RESUME))


if __name__=='__main__':
    unittest.main()
