"""Career level and export regressions."""
import unittest
from career_priority import leadership_tier
from ranked_breakdowns import breakdowns_csv_rows

class CareerReviewTests(unittest.TestCase):
    def test_executive_and_supervisor_categories(self):
        self.assertEqual(leadership_tier('Group Publisher'),4)
        self.assertEqual(leadership_tier('Workplace Experience Supervisor'),0)

    def test_csv_has_title_level_not_eligibility_claim(self):
        jobs=[{'title':'Group Publisher','company':'Example',
               'qualification_match':{'resume_present':True,'fit_index':90}}]
        row=breakdowns_csv_rows(jobs,'3.1.25','test')[0]
        self.assertEqual(row['Career level (title-based)'],'Executive / multi-site leadership')

if __name__=='__main__':
    unittest.main()
