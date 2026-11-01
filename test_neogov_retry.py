"""Government feeds that time out get one more try; real errors do not."""
import ast
import unittest
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request


def load_function(calls, failures_by_slug):
    tree = ast.parse(Path(__file__).with_name('app.py').read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'load_neogov_feeds')

    def iter_public_rss(req, timeout=12):
        slug = req.full_url.rsplit('=', 1)[-1]
        calls.append(slug)
        plan = failures_by_slug.get(slug, [])
        if plan:
            raise plan.pop(0)
        item = ET.fromstring(f'<item><title>Director</title><link>https://www.governmentjobs.com/careers/{slug}/jobs/1234567/x</link></item>')
        yield item

    env = {'ThreadPoolExecutor': ThreadPoolExecutor, 'as_completed': as_completed, 'urlencode': urlencode,
           'Request': Request, 'iter_public_rss': iter_public_rss, 'HTTPError': HTTPError, 'URLError': URLError,
           'ET': ET, 'belongs_to_configured_agency': lambda link, token, source: f'/careers/{token}/' in link,
           'standard_job': lambda title, company, url, *a, **k: {'title': title, 'company': company, 'url': url},
           'rss_workplace_style': lambda item: '',
           'GOVERNMENT_AGENCIES': [('aa', 'Agency A', 'ND'), ('bb', 'Agency B', 'ND'), ('cc', 'Agency C', 'SD')]}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), 'app.py', 'exec'), env)
    return env['load_neogov_feeds']


class NeogovRetryTests(unittest.TestCase):
    def test_timeout_is_retried_once_and_recovers(self):
        calls = []
        load = load_function(calls, {'aa': [URLError('timed out')]})
        jobs, failures, counts = load()
        self.assertEqual(failures, [])
        self.assertEqual(calls.count('aa'), 2)
        self.assertEqual(counts['Agency A (ND)'], 1)
        self.assertEqual(len(jobs), 3)

    def test_second_timeout_is_reported(self):
        calls = []
        load = load_function(calls, {'aa': [URLError('timed out'), URLError('timed out')]})
        jobs, failures, counts = load()
        self.assertEqual(calls.count('aa'), 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(counts['Agency A (ND)'], 0)

    def test_real_errors_are_not_retried(self):
        calls = []
        load = load_function(calls, {'bb': [ValueError('Unexpected RSS response root: error')]})
        jobs, failures, counts = load()
        self.assertEqual(calls.count('bb'), 1)
        self.assertEqual(len(failures), 1)

    def test_state_filter_still_applies(self):
        calls = []
        jobs, failures, counts = load_function(calls, {})('SD')
        self.assertEqual(calls, ['cc'])


if __name__ == '__main__':
    unittest.main()
