"""Regression tests for seniority-aware ranking."""
import unittest
from career_priority import leadership_tier, career_sort_key

class CareerPriorityTests(unittest.TestCase):
    def test_executive_beats_supervisor_with_near_equal_fit(self):
        executive={'title':'Chief Operating Officer','qualification_match':{'fit_index':88}}
        supervisor={'title':'Workplace Experience Supervisor','qualification_match':{'fit_index':89}}
        key=lambda job:(-job['qualification_match']['fit_index'],)
        self.assertLess(career_sort_key(executive,key),career_sort_key(supervisor,key))

    def test_significantly_stronger_evidence_still_wins(self):
        executive={'title':'Chief Operating Officer','qualification_match':{'fit_index':65}}
        manager={'title':'Operations Manager','qualification_match':{'fit_index':90}}
        key=lambda job:(-job['qualification_match']['fit_index'],)
        self.assertLess(career_sort_key(manager,key),career_sort_key(executive,key))

    def test_expected_role_order(self):
        self.assertGreater(leadership_tier('Group Publisher'),leadership_tier('Store Manager'))
        self.assertGreater(leadership_tier('Regional Operations Director'),leadership_tier('Shift Supervisor'))
        self.assertGreater(leadership_tier('Director of Business Development'),leadership_tier('Marketing Specialist'))

if __name__=='__main__':
    unittest.main()
