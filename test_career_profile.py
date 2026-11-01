"""Resume interpretation, career profile answers and transferable role families.

Synthetic resume only: no real person's data belongs in this public repo.
"""
from app_sources import app_source
import ast
import re
import unittest
from pathlib import Path

from career_profile import (LEGACY_DEFAULT_ANSWERS, PROFILE_QUESTIONS, interpret_resume,
                            profile_areas, split_resume)
from qualification_matcher import compile_resume_profile, is_heading_line
from role_families import FAMILIES, explain_job, family_for_title, rank_families, readiness

RESUME = """JANE EXAMPLE
PROFESSIONAL SUMMARY
Visionary, results-driven leader with proven track record in fundraising and public relations.
CORE COMPETENCIES
Advertising | Crisis Communications | Budget Administration
PROFESSIONAL EXPERIENCE
Regional Publisher, Plains Region            March 2019 – Present
Example Media — Herald (Fargo, ND) & Ledger (Minot, ND)
• Oversee budgets for five newspapers totaling $14 million and cut costs 12%.
• Serve as spokesperson and lead crisis communications for the region.
• Lead, mentor and develop department managers.
Circulation Director            2012 – 2019
• Managed distribution and delivery routes across 3 counties.
COMMUNITY LEADERSHIP
• Board Member, Rotary: led strategic planning and local fundraising.
EDUCATION
Bachelor of Business Administration
"""


class HeadingLineTests(unittest.TestCase):
    def test_titles_dates_and_employer_lines_are_not_evidence(self):
        self.assertTrue(is_heading_line('Regional Publisher, Plains Region            March 2019 – Present'))
        self.assertTrue(is_heading_line('Circulation Director 2012 – 2019'))
        self.assertTrue(is_heading_line('Example Media — Herald (Fargo, ND) & Ledger (Minot, ND)'))
        self.assertTrue(is_heading_line('PROFESSIONAL EXPERIENCE'))

    def test_real_bullets_with_dashes_are_kept(self):
        self.assertFalse(is_heading_line('Managed budgets — cut costs 12% (Minot, ND).'))
        self.assertFalse(is_heading_line('• Led sales — 12 reps'))

    def test_title_line_alone_no_longer_proves_editorial_leadership(self):
        profile = compile_resume_profile('Group Publisher, Midwest Region   February 2025 – Present')
        self.assertNotIn('Editorial & cross-functional leadership', profile['evidence'])


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        self.report = interpret_resume(RESUME, {})
        self.grades = {r['area']: r['grade'] for r in self.report['areas']}

    def test_sections_detected(self):
        sections = {section for section, _ in split_resume(RESUME)}
        self.assertTrue({'summary', 'skills', 'experience', 'volunteer'} <= sections)

    def test_grades_reflect_where_and_how_a_claim_appears(self):
        self.assertEqual(self.grades['Financial & P&L leadership'], 'Proven')        # $14 million, 12%
        self.assertEqual(self.grades['Distribution & logistics'], 'Proven')          # 3 counties
        self.assertEqual(self.grades['Communications & public relations'], 'Described')
        self.assertEqual(self.grades['Fundraising & development'], 'Volunteer')
        self.assertEqual(self.grades['Advertising & sales leadership'], 'Summary')   # skills list only
        self.assertEqual(self.grades['Government administration'], 'Not shown')

    def test_vague_phrases_and_missing_numbers_flagged(self):
        phrases = {v['phrase'] for v in self.report['vague']}
        self.assertTrue({'visionary', 'results-driven', 'proven track record'} <= phrases)
        self.assertTrue(any(p.startswith('Advertising & sales leadership') for p in self.report['prompts']))
        self.assertEqual(self.report['work_bullets'], 4)
        self.assertEqual(self.report['numbered_bullets'], 2)

    def test_profile_yes_confirms_and_no_overrules(self):
        report = interpret_resume(RESUME, {'revenue': 'Yes', 'fundraising': 'No'})
        grades = {r['area']: r['grade'] for r in report['areas']}
        self.assertEqual(grades['Revenue growth & transformation'], 'Confirmed')
        self.assertEqual(grades['Fundraising & development'], 'Overruled')
        self.assertTrue(any('Revenue growth' in p and 'confirmed' in p for p in report['prompts']))


class ProfileAnswerTests(unittest.TestCase):
    def test_answers_map_to_areas(self):
        confirmed, excluded = profile_areas({'ad_sales': 'Partly', 'editorial': 'No', 'sites': 4, 'headcount': 5})
        self.assertIn('Advertising & sales leadership', confirmed)
        self.assertIn('Multi-site business leadership', confirmed)
        self.assertNotIn('Talent & organizational change', confirmed)   # 5 < 10 people
        self.assertIn('Editorial & cross-functional leadership', excluded)

    def test_no_removes_resume_evidence_from_matching(self):
        _, excluded = profile_areas({'spokesperson': 'No'})
        profile = compile_resume_profile(RESUME, (), tuple(excluded))
        self.assertNotIn('Communications & public relations', profile['evidence'])
        self.assertIn('Communications & public relations',
                      compile_resume_profile(RESUME)['evidence'])

    def test_legacy_defaults_keep_the_eight_earlier_confirmations(self):
        confirmed, excluded = profile_areas(LEGACY_DEFAULT_ANSWERS)
        self.assertEqual(excluded, set())
        self.assertEqual(confirmed, {
            'Financial & P&L leadership', 'Revenue growth & transformation',
            'Talent & organizational change', 'Digital transformation',
            'Distribution & logistics', 'Negotiation & vendor management',
            'Multi-site business leadership'})

    def test_every_question_targets_known_areas(self):
        from qualification_matcher import CAPABILITIES
        known = {area for area, _ in CAPABILITIES}
        for q in PROFILE_QUESTIONS:
            self.assertTrue(set(q['confirms']) <= known, q['key'])
            self.assertTrue(set(q.get('excludes', ())) <= known, q['key'])


class RoleFamilyTests(unittest.TestCase):
    CASES = {
        'Group Publisher': 'Media & publishing leadership',
        'General Manager': 'General management & operations',
        'Print Production Manager': 'General management & operations',
        'Advertising Director': 'Sales, advertising & partnerships',
        'Director of Sales': 'Sales, advertising & partnerships',
        'Public Information Officer': 'Communications & public affairs',
        'Director of Community Relations': 'Communications & public affairs',
        'Membership Director': 'Marketing, audience & membership',
        'Director of Development': 'Nonprofit leadership & fundraising',
        'Executive Director': 'Nonprofit leadership & fundraising',
        'President & CEO, Minot Area Chamber of Commerce': 'Community, tourism & economic development',
        'Economic Development Director': 'Community, tourism & economic development',
        'Executive Director, Visit Bismarck': 'Community, tourism & economic development',
        'City Administrator': 'Public administration',
        'Distribution Manager': 'Distribution & logistics',
    }

    def test_titles_map_to_families(self):
        for title, label in self.CASES.items():
            family = family_for_title(title)
            self.assertIsNotNone(family, title)
            self.assertEqual(family['label'], label, title)

    def test_unrelated_titles_have_no_family(self):
        for title in ('Software Engineer', 'Registered Nurse', 'Line Cook', 'Program Manager'):
            self.assertIsNone(family_for_title(title), title)

    def test_readiness_rewards_proof_over_description(self):
        family = next(f for f in FAMILIES if f['key'] == 'communications')
        described = readiness(family, {a: 'Described' for a in family['skills']})['score']
        proven = readiness(family, {a: 'Proven' for a in family['skills']})['score']
        summary = readiness(family, {a: 'Summary' for a in family['skills']})['score']
        self.assertEqual(proven, 100)
        self.assertGreater(proven, described)
        self.assertGreater(described, summary)
        self.assertEqual(readiness(family, {})['score'], 0)

    def test_rank_families_puts_shown_skills_first(self):
        grades = {'Communications & public relations': 'Proven', 'Community partnerships': 'Proven',
                  'Audience & marketing development': 'Proven'}
        ranked = rank_families(grades)
        self.assertEqual(ranked[0]['key'], 'communications')
        self.assertEqual(len(ranked), len(FAMILIES))

    def test_job_explanation_uses_only_description_matches(self):
        q = {'resume_matches': [{'area': 'Communications & public relations', 'match_origin': 'Job description'},
                                {'area': 'Operations leadership', 'match_origin': 'Job title only'}],
             'confirmed_only': [{'area': 'Fundraising & development'}],
             'not_documented': [{'area': 'Government administration'}]}
        out = explain_job('Public Information Officer', q, True)
        self.assertEqual(out['family'], 'Communications & public affairs')
        self.assertEqual(out['transfers'], ['Communications & public relations'])
        self.assertEqual(out['confirmed'], ['Fundraising & development'])
        self.assertEqual(out['gaps'], ['Government administration'])


class RoleClassificationTests(unittest.TestCase):
    """The app admits adjacent family titles but still excludes specialists."""
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(app_source())
        wanted = {'role_classification', 'ROLE_PATTERNS', 'SPECIALIST_EXCLUSIONS'}
        body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in wanted) or
                (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in wanted for t in n.targets))]
        env = {'re': re, 'family_for_title': family_for_title}
        exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), 'app.py', 'exec'), env)
        cls.classify = staticmethod(env['role_classification'])

    def test_adjacent_titles_now_admitted(self):
        for title in ('Advertising Director', 'Public Information Officer', 'Director of Development',
                      'President & CEO, Minot Area Chamber of Commerce', 'Print Production Manager'):
            self.assertIsNotNone(self.classify(title), title)

    def test_preset_titles_keep_their_scores(self):
        self.assertEqual(self.classify('City Administrator'), ('Government leadership', 15))
        self.assertEqual(self.classify('Advertising Director'), ('Sales, advertising & partnerships', 10))

    def test_specialists_still_excluded(self):
        for title in ('Director of Nursing', 'Clinical Director', 'Communications Engineer Architect'):
            self.assertIsNone(self.classify(title), title)


if __name__ == '__main__':
    unittest.main()


class DocumentedDutyPrecheckTests(unittest.TestCase):
    """The cheap pre-check must equal the full assessment's description-origin count."""
    def test_precheck_matches_full_assessment(self):
        from qualification_matcher import assess_job_qualifications, documented_duty_count
        profile = compile_resume_profile(RESUME)
        texts = [
            'Manage budgets and forecasts; lead crisis communications and media relations; oversee distribution routes.',
            'Coordinate volunteers.',
            'Oversee fundraising, donor relations and sponsorships. Mentor staff. Negotiate vendor contracts. '
            'Grow digital audience and web traffic. Lead strategic planning with the board.' * 3,
            '',
        ]
        for text in texts:
            job = {'title': 'Partner Experience Lead', 'description': text, 'company': 'X', 'location': 'Fargo, ND'}
            full = assess_job_qualifications(job, profile, RESUME)
            expected = sum(1 for m in full['resume_matches'] if m.get('match_origin') != 'Job title only')
            self.assertEqual(documented_duty_count(job, profile), expected, text[:40])
