"""No-network status reporting tests for working, empty and unavailable boards."""
import ast
from concurrent.futures import Future
from pathlib import Path
from urllib.error import HTTPError, URLError
import unittest


def load_retrieve_boards():
    source=Path(__file__).with_name('app.py').read_text(encoding='utf-8')
    module=ast.parse(source)
    fn=next(x for x in module.body if isinstance(x,ast.FunctionDef)
            and x.name=='retrieve_boards')
    env={
        'HTTPError':HTTPError,'URLError':URLError,'TimeoutError':TimeoutError,
        'ValueError':ValueError,'TypeError':TypeError,'KeyError':KeyError,
        'OSError':OSError
    }
    class Executor:
        def __init__(self,max_workers):
            self.max_workers=max_workers
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def submit(self,callback,record):
            future=Future()
            try:
                future.set_result(callback(record))
            except Exception as exc:
                future.set_exception(exc)
            return future
    env['ThreadPoolExecutor']=Executor
    env['as_completed']=lambda futures:list(futures)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],
                 type_ignores=[])),'app.py','exec'),env)
    return env['retrieve_boards']


class SourceHealthTests(unittest.TestCase):
    def test_active_empty_and_failed_are_distinct(self):
        def reader(row):
            if row[0]=='bad':
                raise URLError('unavailable')
            if row[0]=='empty':
                return []
            return [{'title':'Director of Operations'}]
        jobs,failures,health=load_retrieve_boards()(
            [('ok','Working board'),('empty','Empty board'),
             ('bad','Failed board')],reader)
        self.assertEqual(len(jobs),1)
        self.assertEqual(len(failures),1)
        self.assertEqual({r['board']:r['status'] for r in health},
                         {'Working board':'Active',
                          'Empty board':'Empty','Failed board':'Failed'})
        self.assertEqual(sum(r['records'] for r in health),1)

    def test_failure_is_not_misreported_as_empty(self):
        jobs,failures,health=load_retrieve_boards()(
            [('broken','Broken')],
            lambda _:(_ for _ in ()).throw(ValueError('bad API')))
        self.assertEqual(jobs,[])
        self.assertEqual(health[0]['status'],'Failed')
        self.assertIn('ValueError',failures[0])

    def test_no_boards_is_legitimate_empty(self):
        self.assertEqual(load_retrieve_boards()([],lambda _:[]),
                         ([],[],[]))


if __name__=='__main__':
    unittest.main()
