"""Regression tests for workplace-title screening and remote source policy.

Run with: python -m unittest discover -s tests -v
"""
import unittest
from job_workflow import explicitly_remote_title, permitted_remote_source


class RemotePolicyTests(unittest.TestCase):
    def test_explicit_remote_titles(self):
        titles = (
            "Chief Operating Officer (Remote)",
            "Director, Remote - US",
            "Vice President | Remote, USA",
            "Group Publisher - Remote",
            "Remote - VP Operations",
            "CEO (Remote/USA)",
            "General Manager - Remote (US)",
            "Remote-only Executive",
            "100% Remote Director",
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(explicitly_remote_title(title))

    def test_nonremote_titles_do_not_trigger(self):
        titles = (
            "Director of Remote Sensing",
            "Remote Work Coordinator",
            "Director, Hybrid",
            "General Manager - On-site",
            "Director of Remote Team Engagement",
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(explicitly_remote_title(title))

    def test_remote_private_employer_is_excluded(self):
        self.assertFalse(permitted_remote_source({
            "source": "Greenhouse", "company": "Example Corp", "government": False
        }))

    def test_mayo_remote_exception(self):
        self.assertTrue(permitted_remote_source({
            "source": "Mayo Clinic", "company": "Mayo Clinic", "government": False
        }))
        self.assertFalse(permitted_remote_source({
            "source": "Mayo Clinic", "company": "Unrelated Employer", "government": False
        }))

    def test_public_sector_requires_both_flag_and_trusted_source(self):
        for source in ("NEOGOV", "NEOED Schooljobs", "NYC Open Data"):
            with self.subTest(source=source):
                self.assertTrue(permitted_remote_source({
                    "source": source, "company": "Public Agency", "government": True
                }))
                self.assertFalse(permitted_remote_source({
                    "source": source, "company": "Public Agency", "government": False
                }))
        self.assertFalse(permitted_remote_source({
            "source": "Private Board", "company": "Government Agency",
            "government": True
        }))


if __name__ == "__main__":
    unittest.main()
