"""Offline checks for additional public career-board coverage.

The actual employer-board identities are externally verified; this test does
not pretend a currently published job or working API has been confirmed.
"""
import ast
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
import unittest

from posting_metadata import affirmative, declared_arrangement

BASE = Path(__file__).with_name('job_sources.json')
EXPECTED = {
    'greenhouse': {
        'axios', 'forbes', 'nationalpublicradioinc',
        'propublica', 'semafor', 'voxmedia',
    },
    'lever': {'morningbrew', 'standtogether'},
    'smartrecruiters': {
        'CityofPhiladelphia', 'InformaGroupPlc',
        'NBCUniversal3', 'RedBull',
    },
}
PROVIDERS = (
    'neogov', 'neoed', 'greenhouse', 'ashby', 'smartrecruiters',
    'lever', 'workable', 'mayo',
)


class CareerCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads(BASE.read_text(encoding='utf-8'))

    def test_schema_and_exactly_12_additional_verified_boards(self):
        self.assertEqual(self.catalog['schema_version'],1)
        self.assertEqual(sum(len(self.catalog[x]) for x in PROVIDERS),158)
        for group,ids in EXPECTED.items():
            current={record['id'] for record in self.catalog[group]}
            self.assertTrue(ids.issubset(current),f'{group}: {ids-current}')

    def test_no_duplicate_ids_within_providers(self):
        for provider in PROVIDERS:
            ids=[entry['id'].lower() for entry in self.catalog[provider]]
            self.assertEqual(len(ids),len(set(ids)),provider)
            self.assertTrue(all(entry['name'].strip() for entry in self.catalog[provider]))

    def test_new_public_board_links_are_provider_owned(self):
        urls={
            'greenhouse':'https://job-boards.greenhouse.io/',
            'lever':'https://jobs.lever.co/',
            'smartrecruiters':'https://jobs.smartrecruiters.com/',
        }
        for provider,ids in EXPECTED.items():
            for record in self.catalog[provider]:
                if record['id'] in ids:
                    self.assertEqual(
                        record['career_page'],
                        urls[provider]+record['id'])
                    if provider=='smartrecruiters':
                        self.assertIs(type(record['government']),bool)

    def test_original_board_counts_retained(self):
        self.assertEqual(len(self.catalog['neogov']),85)
        self.assertEqual(len(self.catalog['neoed']),9)
        self.assertEqual(len(self.catalog['mayo']),1)
        self.assertEqual(len(self.catalog['workable']),11)
        self.assertEqual(len(self.catalog['ashby']),12)


class SmartRecruitersDetailTests(unittest.TestCase):
    def test_bounded_details_skip_old_and_remote_and_keep_real_urls(self):
        source=Path(__file__).with_name('app.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        func=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                  and n.name=='load_smartrecruiters_boards')
        func.decorator_list=[]
        module=ast.fix_missing_locations(ast.Module(body=[func],type_ignores=[]))
        recent=date.today().isoformat()
        old=(date.today()-timedelta(days=50)).isoformat()
        def posting(id_,name,when,style='ONSITE'):
            return {
                'id':id_, 'name':name,'releasedDate':when,
                'locationType':style,
                'location':{'country':'us','city':'Philadelphia','region':'PA'},
            }
        listing=[
            posting('ok1','Director of Operations',recent,'HYBRID'),
            posting('old1','VP of Operations',old),
            posting('remote1','Director of Operations',recent,'REMOTE'),
            posting('missing1','Director of Operations',recent),
        ]
        calls=[]
        def fetch_json(url,timeout=None):
            calls.append(url)
            if '/postings?' in url:
                return {'content':listing}
            if url.endswith('/postings/missing1'):
                return {'jobAd':{'sections':{}},'locationType':'ONSITE'}
            return {'postingUrl':'https://jobs.smartrecruiters.com/Example/ok1',
                    'locationType':'HYBRID',
                    'jobAd':{'sections':{'jobDescription':{'text':'Lead teams'},
                                        'qualifications':{'text':'P&L required'}}}}
        class BoundedExecutor:
            def __init__(self,max_workers):
                assert max_workers==3
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def map(self,fn,items):
                return map(fn,items)
        def standard_job(title,company,url,location,description,source,
                         remote=False,salary='',posted=None,eligible=True,
                         gov=False,declared_style=''):
            return {'title':title,'url':url,'location':location,
                    'description':description,'posted':posted,
                    'style':declared_style,'gov':gov} if url else None
        def retrieve_boards(boards,worker,max_workers=8):
            return [job for board in boards for job in worker(board)], []
        env={
            'fetch_json':fetch_json,'ThreadPoolExecutor':BoundedExecutor,
            'date':date,'timedelta':timedelta,'MAX_POSTING_AGE_DAYS':45,
            'quote':quote,'urlencode':urlencode,
            'role_classification':lambda name: ('leadership',12),
            'parse_posted_date':date.fromisoformat,
            'declared_arrangement':declared_arrangement,
            'affirmative':affirmative,
            'standard_job':standard_job,
            'retrieve_boards':retrieve_boards,
            'SMARTRECRUITERS_BOARDS':(('Example','Example',False),),
            'HTTPError':HTTPError,'URLError':URLError,'TimeoutError':TimeoutError,
            'ValueError':ValueError,'TypeError':TypeError,'OSError':OSError,
        }
        exec(compile(module,'app.py','exec'),env)
        jobs,failures=env['load_smartrecruiters_boards']()
        self.assertEqual(len(jobs),1)
        self.assertEqual(failures,[])
        self.assertEqual(jobs[0]['url'],
                         'https://jobs.smartrecruiters.com/Example/ok1')
        self.assertEqual(jobs[0]['style'],'Hybrid')
        self.assertIn('P&L required',jobs[0]['description'])
        self.assertFalse(any('old1' in url or 'remote1' in url for url in calls))
        self.assertTrue(any('missing1' in url for url in calls))


if __name__=='__main__':
    unittest.main()
