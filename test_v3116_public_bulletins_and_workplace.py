"""3.1.16: bound and verify government bulletin fallback and RSS work modes."""
import unittest
import xml.etree.ElementTree as ET

from official_bulletins import (
    official_bulletin_url,fetch_official_bulletin,
    enrich_priority_government_jobs
)
from posting_metadata import rss_workplace_style
from test_official_bulletins import FULL,URL,_FakeResponse

JOB={
    'title':'Transmission Section Manager (Mgr 3)',
    'source':'NEOGOV','company':'City of Seattle',
    'url':URL,'description':'Brief announcement and staff responsibilities.'
}


class PublicBulletinFallbackTests(unittest.TestCase):
    def test_print_first_and_validated_detail_fallback(self):
        seen=[]
        def opener(req,timeout=5):
            seen.append(req.full_url)
            if '/newprint/' in req.full_url:
                return _FakeResponse('<html><h1>Job portal</h1></html>',req.full_url)
            return _FakeResponse(FULL,req.full_url)
        text=fetch_official_bulletin(JOB,opener=opener)
        self.assertIn('Five (5) years',text)
        self.assertEqual(len(seen),2)
        self.assertEqual(seen[0],official_bulletin_url(URL))
        self.assertEqual(seen[1],
                         'https://www.governmentjobs.com/careers/seattle/jobs/5491625')

    def test_transient_print_failure_falls_back_to_detail(self):
        seen=[]
        def opener(req,timeout=5):
            seen.append(req.full_url)
            if '/newprint/' in req.full_url:
                raise TimeoutError('simulated timeout')
            return _FakeResponse(FULL,req.full_url)
        self.assertIn('Qualifications',fetch_official_bulletin(JOB,opener=opener))
        self.assertEqual(len(seen),2)

    def test_different_vacancy_same_host_redirect_rejected(self):
        def opener(req,timeout=5):
            return _FakeResponse(
                FULL,'https://www.governmentjobs.com/careers/seattle/jobs/9876543')
        self.assertEqual(fetch_official_bulletin(JOB,opener=opener),'')

    def test_mismatched_agency_or_cross_domain_rejected(self):
        for dest in ('https://www.schooljobs.com/careers/seattle/jobs/5491625',
                     'https://www.governmentjobs.com/careers/boise/jobs/5491625',
                     'https://other.example.com/careers/seattle/jobs/5491625'):
            with self.subTest(dest=dest):
                self.assertEqual(fetch_official_bulletin(
                    JOB,opener=lambda req,timeout=5:
                    _FakeResponse(FULL,dest)),'')

    def test_incomplete_detail_is_not_misrepresented_as_full(self):
        calls=[]
        def opener(req,timeout=5):
            calls.append(req.full_url)
            return _FakeResponse('<html><h1>Loading job...</h1></html>',req.full_url)
        self.assertEqual(fetch_official_bulletin(JOB,opener=opener),'')
        result,stats=enrich_priority_government_jobs(
            [JOB],[JOB],fetch=lambda j:'',limit=1)
        self.assertEqual(stats['full_bulletins'],0)
        self.assertEqual(stats['summary_only'],1)
        self.assertIn('summary only',result[0]['description_source'].lower())

    def test_priority_retrieval_does_not_mutate_original(self):
        jobs=[{**JOB,'url':URL},{'title':'Other','source':'Workable employer',
             'url':'https://example.org/another','description':'Unrelated'}]
        updated,stats=enrich_priority_government_jobs(
            jobs,jobs,fetch=lambda job:FULL,limit=1)
        self.assertEqual(len(updated),2)
        self.assertEqual(stats['attempted'],1)
        self.assertEqual(stats['full_bulletins'],1)
        self.assertNotEqual(updated[0]['description'],jobs[0]['description'])
        self.assertEqual(jobs[0]['description'],JOB['description'])


class RSSWorkplaceMetadataTests(unittest.TestCase):
    @staticmethod
    def xml(text):
        return ET.fromstring(text)

    def test_explicit_label_hybrid(self):
        entry=self.xml('<item><title>Operations Director</title>'
                       '<workplaceType>Hybrid</workplaceType></item>')
        self.assertEqual(rss_workplace_style(entry),'Hybrid')

    def test_namespace_explicit_onsite_and_remote(self):
        item=self.xml('<item xmlns:job="urn:job">'
                      '<job:workArrangement>On-site</job:workArrangement></item>')
        self.assertEqual(rss_workplace_style(item),'On-site')
        item=self.xml('<item><remoteWorkType>Remote</remoteWorkType></item>')
        self.assertEqual(rss_workplace_style(item),'Remote')

    def test_unlabeled_city_and_telework_eligibility_are_not_remote(self):
        for source in (
            '<item><location>Fargo, ND</location><description>Hybrid benefits.</description></item>',
            '<item><teleworkEligible>Yes</teleworkEligible></item>',
            '<item><title>Remote Sensing Director</title></item>'
        ):
            with self.subTest(source=source):
                self.assertEqual(rss_workplace_style(self.xml(source)),'')

    def test_conflicting_workplace_metadata_is_unknown(self):
        item=self.xml('<item><workplaceType>On-site</workplaceType>'
                      '<workArrangement>Remote</workArrangement></item>')
        self.assertEqual(rss_workplace_style(item),'')

    def test_empty_unknown_or_missing_metadata(self):
        self.assertEqual(rss_workplace_style(None),'')
        self.assertEqual(rss_workplace_style(self.xml('<item><workMode>Flexible</workMode></item>')),'')


if __name__ == '__main__':
    unittest.main()
