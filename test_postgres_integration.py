"""Real Postgres tests. CI supplies a disposable database, never production."""
import os,unittest,uuid
from concurrent.futures import ThreadPoolExecutor
from tracker_store import load_remote_workspace,save_remote_workspace,load_workspace_history,WorkspaceConflict,_connect

@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'),'Requires disposable TEST_DATABASE_URL')
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.url=os.environ['TEST_DATABASE_URL'];self.workspace='test-'+uuid.uuid4().hex
    def tearDown(self):
        with _connect(self.url) as conn:
            conn.execute('DELETE FROM ai_job_finder_history WHERE workspace_id=%s',(self.workspace,))
            conn.execute('DELETE FROM ai_job_finder_workspace WHERE workspace_id=%s',(self.workspace,))
    def save(self,revision,note):
        return save_remote_workspace(self.url,self.workspace,[{'Company':'Test','Job Title':'Manager','Status':'Saved','Notes':note}],[],True,expected_revision=revision)
    def test_stale_writer_rejected_and_history_retained(self):
        self.assertEqual(load_remote_workspace(self.url,self.workspace)['revision'],0)
        self.assertEqual(self.save(0,'first'),1)
        self.assertEqual(self.save(1,'second'),2)
        with self.assertRaises(WorkspaceConflict):self.save(1,'stale')
        self.assertEqual(load_remote_workspace(self.url,self.workspace)['jobs'][0]['Notes'],'second')
        self.assertEqual(len(load_workspace_history(self.url,self.workspace)),2)
    def test_two_simultaneous_writers_only_one_wins(self):
        load_remote_workspace(self.url,self.workspace)
        self.save(0,'base')
        def write(note):
            try:return self.save(1,note)
            except WorkspaceConflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(write,['A','B']))
        self.assertCountEqual(outcomes,[2,'conflict'])
    def test_history_bounded_and_legacy_payload_migrates(self):
        load_remote_workspace(self.url,self.workspace)
        with _connect(self.url) as conn:
            conn.execute('INSERT INTO ai_job_finder_workspace (workspace_id,payload) VALUES (%s,%s::jsonb)',
                         (self.workspace,'{"schema_version":1,"jobs":[],"seen":[],"has_baseline":false}'))
        self.assertEqual(load_remote_workspace(self.url,self.workspace)['schema_version'],2)
        for revision in range(23):self.save(revision,str(revision))
        history=load_workspace_history(self.url,self.workspace)
        self.assertEqual(len(history),20)
        self.assertEqual(history[0]['revision'],23)
