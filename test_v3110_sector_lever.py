"""No-network v3.1.10 regressions for degree fields, sector years, Lever health."""
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
import re
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit

from posting_requirements import extract_posting_requirements
from formal_qualification_guardrails import extract_formal_minimums
from career_fit_guardrails import evaluate_career_fit
from qualification_matcher import assess_job_qualifications,compile_resume_profile
from ranked_breakdowns import evidence_index
from posting_metadata import declared_arrangement

RESUME=("Group Newspaper Publisher and Regional Operations Director with "
        "25 years leading P&L, multiple offices, ad sales, marketing, "
        "budgets, managers, vendor contracts, distribution and logistics. "
        "Earned Bachelor's degree in Business Administration.")
CONSTRUCTION_RESUME=(RESUME+" Earned Bachelor's degree in Construction "
                      "Management. Led commercial construction projects for 20 years.")
FINANCE_RESUME=(RESUME+" 10 years in corporate finance, FP&A, "
                "financial modeling and investment analysis.")
WORK=("Manage complex budgets, regional managers, stakeholder relationships, "
      "operational efficiency, revenue, vendor contracts and staff. "*7)


def required(title,desc,resume=RESUME):
    return extract_formal_minimums({'title':title,'description':desc},resume)


def field(title,desc,resume=RESUME):
    return extract_posting_requirements({'title':title,'description':desc},resume)


def scored(title,desc,resume=RESUME):
    return assess_job_qualifications({'title':title,'description':desc},
                 compile_resume_profile(resume,()),resume)


class ConstructionDegreeTests(unittest.TestCase):
    def test_brph_vp_preconstruction_degree_not_business_management(self):
        desc=("<h2>Qualifications</h2><li>Bachelor’s degree in construction "
              "management, engineering, architecture, or a related discipline "
              "is required.</li><li>Minimum 20 years of progressive "
              "construction preconstruction experience required.</li>"+WORK)
        formal=required('VP Preconstruction',desc)
        self.assertGreaterEqual(formal['ranking_caution'],22)
        self.assertTrue(formal['unverified_mandatory'])
        self.assertIn('not documented',formal['checks'][0]['resume_status'])
        fit=scored('VP Preconstruction',desc)
        self.assertGreater(fit['posting_requirement_penalty'],0)
        self.assertGreater(fit['career_fit_penalty'],0)
        self.assertLess(evidence_index(fit),80)
        self.assertEqual(required('VP Preconstruction',desc,CONSTRUCTION_RESUME)
                         ['ranking_caution'],0)

    def test_senior_capital_project_manager_construction_management_degree(self):
        desc=("<h2>Qualification</h2><li>Bachelor's degree in Construction "
              "Management, Engineering, or related field.</li><li>Minimum "
              "8 years of experience managing construction projects.</li>")
        f=required('Senior Capital Project Manager',desc)
        self.assertGreaterEqual(f['ranking_caution'],22)
        p=field('Senior Capital Project Manager',desc)
        self.assertGreater(p['ranking_caution'],0)

    def test_explicit_business_alternative_is_valid(self):
        desc=("<h2>Qualifications</h2><li>Bachelor's degree in Construction "
              "Management, Engineering, or Business Administration required.</li>")
        self.assertEqual(required('Operations Director',desc)['ranking_caution'],0)

    def test_only_related_discipline_not_equivalent_business(self):
        desc=("<h2>Qualifications</h2><li>Bachelor's degree in construction "
              "management, engineering or a related discipline required.</li>")
        self.assertGreater(required('Operations Director',desc)['ranking_caution'],0)

    def test_preferred_technical_degree_still_not_mandatory(self):
        desc=("<h2>Qualifications</h2><li>Bachelor's degree in Engineering, "
              "Operations Management, Business, Industrial Technology, "
              "or related field is preferred.</li>")
        self.assertEqual(required('Operations Manager',desc)['ranking_caution'],0)


class SpecialistExperienceTests(unittest.TestCase):
    def test_imprint_corporate_finance_minimum_is_not_general_budgeting(self):
        desc=("<h2>What We Look For</h2><li>5–10 years of experience in "
              "a finance, data, or analytically intensive role.</li>"
              "<h2>Nice to Have</h2><li>Prior credit card experience.</li>"+WORK)
        checks=field('Manager, Corporate Finance',desc)
        self.assertTrue(any(c['area']=='Corporate finance / FP&A specialization'
                            and c['ranking_caution']>0 for c in checks['checks']),
                        checks)
        q=scored('Manager, Corporate Finance',desc)
        self.assertGreater(q['posting_requirement_penalty'],0)
        self.assertGreater(q['career_fit_penalty'],0)
        self.assertLess(evidence_index(q),85)
        self.assertEqual(field('Manager, Corporate Finance',desc,FINANCE_RESUME)
                         ['ranking_caution'],0)
        self.assertEqual(evaluate_career_fit(
            {'title':'Manager, Corporate Finance'},FINANCE_RESUME)['penalty'],0)

    def test_construction_years_in_minimums_are_not_generic_project_management(self):
        desc=("<h2>Qualifications</h2><li>Minimum 20 years of construction-related "
              "experience including commercial preconstruction "
              "and estimating leadership.</li>")
        checks=field('VP Preconstruction',desc)
        self.assertGreater(checks['ranking_caution'],0)
        self.assertGreater(evaluate_career_fit(
            {'title':'VP Preconstruction'},RESUME)['penalty'],0)

    def test_transferable_operational_roles_not_specialist_penalized(self):
        for title in ('Regional Operations Manager','Partnership Director',
                      'Procurement Manager','Distribution Director'):
            with self.subTest(title=title):
                q=scored(title,WORK)
                self.assertEqual(q['posting_requirement_penalty'],0)
                self.assertEqual(q['career_fit_penalty'],0)


def extract_lever_loader():
    tree=ast.parse(Path(__file__).with_name('app.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=='load_lever_employers')
    fn.decorator_list=[]
    return compile(ast.fix_missing_locations(
        ast.Module(body=[fn],type_ignores=[])),'app.py','exec')


class LeverSourceHealthTests(unittest.TestCase):
    def fake_implementation(self,partial=False):
        day=1792108800000  # 2026-10-16 (test date is not read from clock)
        recent=[
            {'text':'Operations Manager','hostedUrl':f'https://jobs.lever.co/momentshospice-2/job{i}',
             'createdAt':day,'categories':{'location':'Minneapolis, MN'},
             'workplaceType':'on-site',
             'descriptionPlain':'Lead managers and operations',
             'additionalPlain':'Real job qualification text'}
            for i in range(115)
        ]
        seen=[]
        def fetch_json(url,timeout=None):
            seen.append(url)
            slug=urlsplit(url).path.rsplit('/',1)[-1]
            offset=int(parse_qs(urlsplit(url).query).get('skip',[0])[0])
            if slug=='momentshospice-2':
                return recent[offset:offset+100]
            if slug=='networkconnex':
                return []
            if slug=='kcasbio':
                raise URLError('provider unavailable')
            if slug=='billboarder':
                if offset:
                    if partial:raise TimeoutError('partial provider failure')
                    return []
                return recent[:100]
            raise AssertionError(slug)
        def standard_job(title,company,url,location,description,source,
                         remote,salary,posted,eligible,declared_style):
            return {'title':title,'company':company,'url':url,'location':location,
                    'description':description,'source':source,
                    'eligible':eligible,'date':'2026-10-16',
                    'work_style':'On-site','remote':False}
        env={'ThreadPoolExecutor':ThreadPoolExecutor,'as_completed':as_completed,
             'fetch_json':fetch_json,
             'quote':quote,'re':re,'states_in_location':lambda loc:['MN'] if 'MN' in loc else [],
             'declared_arrangement':declared_arrangement,
             'us_remote_eligible':lambda loc:False,
             'is_recent_posting':lambda job:job.get('date')=='2026-10-16',
             'standard_job':standard_job,
             'HTTPError':HTTPError,'URLError':URLError,'TimeoutError':TimeoutError,
             'ValueError':ValueError,'TypeError':TypeError,
             'KeyError':KeyError,'OSError':OSError,
             'LEVER_BOARDS':(
                ('momentshospice-2','Moments Hospice'),
                ('networkconnex','Network Connex'),
                ('kcasbio','KCAS Bio'),
                ('billboarder','Billboarder'),
             )}
        exec(extract_lever_loader(),env)
        return env['load_lever_employers'],seen

    def test_second_page_pagination_and_per_board_diagnostics(self):
        load,calls=self.fake_implementation()
        jobs,failures,health=load()
        indexed={x['board']:x for x in health}
        self.assertEqual(indexed['Moments Hospice']['provider_records'],115)
        self.assertEqual(indexed['Moments Hospice']['pages'],2)
        self.assertEqual(indexed['Moments Hospice']['recent_us'],115)
        self.assertEqual(indexed['Moments Hospice']['status'],'Active')
        self.assertTrue(any('skip=100' in url for url in calls))
        self.assertEqual(indexed['Network Connex']['status'],'Empty')
        self.assertEqual(indexed['Network Connex']['provider_records'],0)
        self.assertEqual(indexed['KCAS Bio']['status'],'Failed')
        self.assertTrue(any('KCAS Bio' in e for e in failures))
        self.assertGreaterEqual(len(jobs),115)

    def test_second_page_failure_keeps_first_page_and_marks_partial(self):
        load,_=self.fake_implementation(partial=True)
        jobs,failures,health=load()
        indexed={x['board']:x for x in health}
        self.assertEqual(indexed['Billboarder']['status'],'Partial')
        self.assertEqual(indexed['Billboarder']['pages'],1)
        self.assertEqual(indexed['Billboarder']['records'],100)
        self.assertTrue(any('Billboarder' in e for e in failures))


if __name__=='__main__':
    unittest.main()
