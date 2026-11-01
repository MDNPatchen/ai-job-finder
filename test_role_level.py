"""Minimum role level: hide roles below the level the person is looking for."""
import unittest

from job_workflow import MINIMUM_LEVELS, meets_minimum_level, preferences_allow
import saved_searches


class MinimumLevelTests(unittest.TestCase):
    BELOW = ('Marketing Coordinator', 'Communications Specialist', 'Executive Assistant to the CEO',
             'Data Analyst', 'Shift Supervisor', 'Administrative Assistant')
    MANAGER = ('Communications Manager', 'Assistant General Manager', 'Public Information Officer')
    DIRECTOR_UP = ('Director of Development', 'Executive Director', 'Group Publisher',
                   'Vice President of Sales', 'City Administrator', 'Regional Operations Manager')

    def test_manager_and_above(self):
        for title in self.BELOW:
            self.assertFalse(meets_minimum_level(title, 'Manager and above'), title)
        for title in self.MANAGER + self.DIRECTOR_UP:
            self.assertTrue(meets_minimum_level(title, 'Manager and above'), title)

    def test_director_and_above(self):
        for title in self.BELOW + ('Communications Manager', 'Assistant General Manager'):
            self.assertFalse(meets_minimum_level(title, 'Director and above'), title)
        for title in self.DIRECTOR_UP:
            self.assertTrue(meets_minimum_level(title, 'Director and above'), title)

    def test_all_levels_and_missing_setting_keep_everything(self):
        for title in self.BELOW:
            self.assertTrue(meets_minimum_level(title, 'All levels'))
            self.assertTrue(meets_minimum_level(title, None))

    def test_applied_through_preferences(self):
        job = {'title': 'Marketing Coordinator', 'work_style': 'On-site'}
        self.assertFalse(preferences_allow(job, ['ND'], {'minimum_level': 'Manager and above'}))
        self.assertTrue(preferences_allow(job, ['ND'], {}))

    def test_default_option_first_and_saved_with_searches(self):
        self.assertEqual(MINIMUM_LEVELS[0], 'Manager and above')
        saved = saved_searches.upsert([], 'Directors', {'f_min_level': 'Director and above'})
        target = {}
        saved_searches.apply(target, saved[0]['filters'], {'f_min_level': list(MINIMUM_LEVELS)})
        self.assertEqual(target['f_min_level'], 'Director and above')


if __name__ == '__main__':
    unittest.main()
