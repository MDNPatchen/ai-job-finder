"""Workday reader: keyword search, title screen, bounded details, honest coverage."""
import re
import unittest
from datetime import date, timedelta

from workday_source import board_root, cache_key, fetch_board, public_url

TODAY = date(2026, 11, 1)
BOARD = ('avera|wd5|avera-careers', 'Avera Health')
ROOT = board_root('avera', 'wd5', 'avera-careers')


def classify(title):
    return bool(re.search(r'director|manager|executive', title or '', re.I))


def normalize(title, company, url, location, description, source, remote, salary, posted, eligible, gov, style):
    return {'title': title, 'company': company, 'url': url, 'location': location, 'source': source,
            'date': posted, 'work_style': style, 'description': description}


def parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


class FakeWorkday:
    def __init__(self, postings, details, fail_list=False):
        self.postings, self.details, self.fail_list = postings, details, fail_list
        self.posts, self.gets = [], []

    def post(self, url, body):
        self.posts.append((url, body))
        if self.fail_list:
            raise OSError('timed out')
        term = body['searchText']
        rows = [p for p in self.postings if term in p['title'].lower()]
        page = rows[body['offset']:body['offset'] + body['limit']]
        return {'total': len(rows), 'jobPostings': page}

    def get(self, url):
        self.gets.append(url)
        path = url[len(ROOT):]
        if path not in self.details:
            raise OSError('missing')
        return self.details[path]


def posting(i, title):
    return {'title': title, 'externalPath': f'/job/Sioux-Falls-SD/{i}', 'locationsText': 'Sioux Falls, SD'}


def detail(title, days_old=3, country='United States of America', remote=''):
    return {'jobPostingInfo': {'title': title, 'jobDescription': '<p>Lead operations.</p>',
                               'location': 'Sioux Falls, SD', 'startDate': str(TODAY - timedelta(days=days_old)),
                               'country': {'descriptor': country}, 'remoteType': remote,
                               'externalUrl': f'https://avera.wd5.myworkdayjobs.com/en-US/avera-careers/job/x/{title}'},
            'hiringOrganization': {'name': 'Avera McKennan'}}


class WorkdayTests(unittest.TestCase):
    def run_board(self, wd, **kw):
        return fetch_board(BOARD, wd.post, wd.get, normalize, classify, parse_date, 45, TODAY, **kw)

    def test_only_matching_titles_get_details(self):
        wd = FakeWorkday([posting(1, 'Director of Operations'), posting(2, 'Registered Nurse Manager'),
                          posting(3, 'Housekeeper')],
                         {'/job/Sioux-Falls-SD/1': detail('Director of Operations'),
                          '/job/Sioux-Falls-SD/2': detail('Registered Nurse Manager', remote='Hybrid')},)
        jobs = self.run_board(wd, terms=('director', 'manager', 'housekeeper'))
        self.assertEqual({j['title'] for j in jobs}, {'Director of Operations', 'Registered Nurse Manager'})
        self.assertEqual(len(wd.gets), 2)                       # housekeeper never fetched
        self.assertEqual(jobs[0]['source'], 'Workday')
        self.assertEqual(jobs[0]['company'], 'Avera McKennan')   # hiring organization wins
        self.assertTrue(all(j['url'].startswith('https://avera.wd5.myworkdayjobs.com/') for j in jobs))
        self.assertEqual({j['work_style'] for j in jobs}, {'', 'Hybrid'})

    def test_old_foreign_and_duplicate_postings_skipped(self):
        wd = FakeWorkday([posting(1, 'Director A'), posting(2, 'Director B'), posting(3, 'Director C')],
                         {'/job/Sioux-Falls-SD/1': detail('Director A', days_old=60),
                          '/job/Sioux-Falls-SD/2': detail('Director B', country='Canada'),
                          '/job/Sioux-Falls-SD/3': detail('Director C')})
        jobs = self.run_board(wd, terms=('director', 'director'))
        self.assertEqual([j['title'] for j in jobs], ['Director C'])
        self.assertEqual(len(wd.gets), 3)                       # duplicates fetched once

    def test_coverage_is_reported_when_capped(self):
        rows = [posting(i, f'Director {i}') for i in range(60)]
        details = {f'/job/Sioux-Falls-SD/{i}': detail(f'Director {i}') for i in range(60)}
        wd = FakeWorkday(rows, details)
        jobs = self.run_board(wd, terms=('director',), pages_per_term=2, max_details=10)
        self.assertEqual(len(jobs), 10)
        self.assertTrue(jobs.diagnostics['truncated'])
        self.assertEqual(jobs.diagnostics['listed_records'], 40)
        self.assertEqual(len(wd.posts), 2)
        self.assertEqual(wd.posts[1][1]['offset'], 20)

    def test_first_page_failure_raises_so_board_shows_failed(self):
        with self.assertRaises(OSError):
            self.run_board(FakeWorkday([], {}, fail_list=True))

    def test_detail_failures_are_counted(self):
        wd = FakeWorkday([posting(1, 'Director A'), posting(2, 'Director B')],
                         {'/job/Sioux-Falls-SD/1': detail('Director A')})
        jobs = self.run_board(wd, terms=('director',))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs.diagnostics['failed_details'], 1)

    def test_urls_and_cache_keys(self):
        self.assertEqual(ROOT, 'https://avera.wd5.myworkdayjobs.com/wday/cxs/avera/avera-careers')
        self.assertEqual(public_url('avera', 'wd5', 'avera-careers', '/job/x/1'),
                         'https://avera.wd5.myworkdayjobs.com/en-US/avera-careers/job/x/1')
        a = cache_key(ROOT + '/jobs', {'searchText': 'director', 'offset': 0})
        b = cache_key(ROOT + '/jobs', {'searchText': 'manager', 'offset': 0})
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main()
