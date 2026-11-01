"""Offline checks for additional public career-board coverage.

The actual employer-board identities are externally verified; this test does
not pretend a currently published job or working API has been confirmed.
"""
from app_sources import app_source
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
ORIGINAL_IDS = {"neogov": ["CGA", "LOUISIANA", "Pittsburgh", "alabama", "alachua", "alaska", "boiseid", "boston", "brokenarrowok", "broward", "burlingtonvt", "cabq", "centennial", "charlevoix", "charlottecountyfl", "clarkcounty", "cleveland", "colorado", "colubbocktx", "columbusoh", "concordnh", "countyofdane", "dakota", "deschutes", "desmoines", "duluthmn", "dupageco", "durhamnc", "eauclaire", "erieco", "fairfaxcounty", "fargond", "flaglercounty", "greenvillesc", "gwinnett", "harriscountytx", "hennepin", "honolulu", "hopkinsvilleky", "indianapolis", "iowa", "juneauwi", "kingcounty", "lacounty", "lakecountyil", "lincolnne", "littlerock", "livingstoncounty", "madisonmt", "madisonwi", "miamifl", "minneapolismn", "mississippi", "mohavecountyaz", "montgomerycountymd", "nashville", "nassaucountyny", "nccde", "newjersey", "neworleans", "njjudiciary", "oc", "olmsted", "pinalcounty", "polkia", "portlandor", "raleighnc", "rhodeisland", "riverside", "saccity", "saginawmi", "sandiego", "santaclara", "sdcounty", "seattle", "seminolecountyfl", "sheboygancounty", "siouxfallssd", "stlouis", "utah", "volusiaco", "washington", "waynecountyny", "wichita", "wv", "wyoming"], "neoed": ["cccd", "duvalschools", "ggusd", "laneedu", "palmdalesd", "pasadenaedu", "sdlancaster", "sewanee", "venturausd"], "greenhouse": ["aksengineeringforestryllc", "amn", "axios", "boldbusiness", "brph", "clear", "courtyardinc", "energyprojectsolutionsllc", "forbes", "imaginepediatrics", "industrialelectricmanufacturing", "nationalpublicradioinc", "powerdigitalmarketing", "propublica", "riseamg", "sbusa", "semafor", "spsnorthamerica", "unitedveincenters", "voxmedia", "winnerscirclegroupoftexas1", "wpp"], "ashby": ["alternativepayments", "cardless", "claylabs", "ember-life-sciences", "encord", "imprint", "partly.com", "rain", "redesign health", "remodelboom", "talkiatry", "tensec"], "smartrecruiters": ["Bertelsmann-Jobs", "CityAndCountyOfSanFrancisco1", "CityofPhiladelphia", "Dexterra", "InformaGroupPlc", "InternationalDairyQueen", "KIPP", "MadeByFernLLC", "NBCUniversal3", "PSICRO", "RedBull", "prosidianconsulting"], "lever": ["billboarder", "kcasbio", "momentshospice-2", "morningbrew", "networkconnex", "standtogether"], "workable": ["agcp", "atria-health", "futureplc", "hoa-talent", "johnson-mark-pc", "keller-executive-search", "lv-petroleum", "nakedmd", "pj-fitz", "the-common-market", "yugo"], "mayo": ["mayo-clinic"]}
PROVIDERS = (
    'neogov', 'neoed', 'greenhouse', 'ashby', 'smartrecruiters',
    'lever', 'workable', 'mayo',
)


class CareerCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads(BASE.read_text(encoding='utf-8'))

    def test_schema_and_previously_verified_boards_present(self):
        self.assertEqual(self.catalog['schema_version'],1)
        self.assertGreaterEqual(sum(len(self.catalog[x]) for x in PROVIDERS),212)
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

    def test_original_boards_retained(self):
        # Boards are never deleted; a dead board is kept with enabled: false.
        for provider,ids in ORIGINAL_IDS.items():
            current={x['id'] for x in self.catalog[provider]}
            self.assertTrue(set(ids).issubset(current),f'{provider}: {set(ids)-current}')
        self.assertIn('nccde',{x['id'] for x in self.catalog['neogov']})
        self.assertGreaterEqual(len({x['state'] for x in self.catalog['neogov']+
                                     self.catalog['neoed']}),49)
        self.assertEqual(len(self.catalog['mayo']),1)

    def test_disabled_boards_explain_why(self):
        for provider in PROVIDERS:
            for record in self.catalog[provider]:
                if record.get('enabled',True) is False:
                    self.assertTrue(record.get('note','').strip(),f"{provider}/{record['id']}")

    def test_added_boards_are_live_verified_and_well_formed(self):
        pages={'neogov':'https://www.governmentjobs.com/careers/',
               'greenhouse':'https://job-boards.greenhouse.io/',
               'lever':'https://jobs.lever.co/','ashby':'https://jobs.ashbyhq.com/',
               'smartrecruiters':'https://jobs.smartrecruiters.com/',
               'workable':'https://apply.workable.com/'}
        added=0
        for provider,prefix in pages.items():
            for record in self.catalog[provider]:
                if 'verified' not in record:
                    continue
                added+=1
                self.assertRegex(record['verified'],r'^\d{4}-\d{2}-\d{2}$')
                self.assertEqual(record['career_page'],prefix+record['id'])
                if provider=='neogov':
                    self.assertRegex(record['state'],r'^[A-Z]{2}$')
                if provider=='smartrecruiters':
                    self.assertIs(type(record['government']),bool)
        self.assertGreaterEqual(added,53)

    def test_workday_entries_are_live_verified_and_well_formed(self):
        import re as _re
        for record in self.catalog.get('workday', []):
            self.assertRegex(record['wd'], r'^wd\d{1,3}$')
            self.assertRegex(record['site'], r'^[A-Za-z0-9_-]+$')
            self.assertRegex(record.get('verified', ''), r'^\d{4}-\d{2}-\d{2}$')
            self.assertEqual(record['career_page'],
                             f"https://{record['id']}.{record['wd']}.myworkdayjobs.com/{record['site']}")

    def test_app_loader_accepts_catalog(self):
        tree=ast.parse(app_source())
        wanted={'read_job_sources','VALID_SOURCE_GROUPS','US_STATES'}
        body=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in wanted) or
              (isinstance(n,ast.Assign) and any(getattr(t,'id',None) in wanted for t in n.targets))]
        import re as _re
        env={'json':json,'re':_re,'Path':Path,'SOURCE_CATALOG_FILE':BASE}
        exec(compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),'app.py','exec'),env)
        loaded=env['read_job_sources'](BASE)
        enabled=sum(record.get('enabled',True) is not False for record in self.catalog['neogov'])
        self.assertEqual(len(loaded['neogov']),enabled)
        self.assertNotIn('boldbusiness',{token for token,_ in loaded['greenhouse']})
        for token,name in loaded.get('workday',()):
            self.assertEqual(token.count('|'),2,name)


class SmartRecruitersDetailTests(unittest.TestCase):
    def test_bounded_details_skip_old_and_remote_and_keep_real_urls(self):
        source=app_source()
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
            jobs=[job for board in boards for job in worker(board)]
            return jobs, [], [{'status':'Active','board':'Example','records':len(jobs)}]
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
        jobs,failures,health=env['load_smartrecruiters_boards']()
        self.assertEqual(health[0]['records'],1)
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
