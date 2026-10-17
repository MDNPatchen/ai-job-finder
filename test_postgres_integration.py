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
    def test_restart_backup_restore_preserves_applications_and_employer_checks(self):
        from tracker_store import export_workspace_json,import_workspace_json
        from tracker_sync import apply_workspace,snapshot
        from workspace_recovery import prepare_restore
        evidence={'posting-id':{'checked_at':'2026-10-17T10:00:00Z','posting':{'url':'https://example.org/1'}}}
        jobs=[{'Company':'Test','Job Title':'Director','Status':'Applied','Notes':'Original résumé notes',
               'Follow-up Date':'2026-10-21','Job URL':'https://example.org/1'}]
        save_remote_workspace(self.url,self.workspace,jobs,['a'*32],True,expected_revision=0,employer_evidence=evidence)
        # A new connection/session reloads all durable fields.
        loaded=load_remote_workspace(self.url,self.workspace)
        backup=export_workspace_json(loaded['jobs'],loaded['seen'],loaded['has_baseline'],loaded['employer_evidence'])
        save_remote_workspace(self.url,self.workspace,[],[],False,expected_revision=1)
        current=load_remote_workspace(self.url,self.workspace)
        restored,_=prepare_restore(current,import_workspace_json(backup.encode()),replace=True)
        fresh={};apply_workspace(fresh,restored)
        save_remote_workspace(self.url,self.workspace,fresh['jobs'],fresh['seen_jobs'],fresh['search_baseline'],
            expected_revision=current['revision'],employer_evidence=fresh['employer_checks'])
        final=load_remote_workspace(self.url,self.workspace)
        self.assertEqual(final['jobs'],loaded['jobs']);self.assertEqual(final['seen'],['a'*32])
        self.assertEqual(final['employer_evidence'],evidence);self.assertEqual(final['revision'],3)
        # Recovery versions remain available after restoring a backup.
        history=load_workspace_history(self.url,self.workspace)
        self.assertEqual([x['revision'] for x in history],[3,2,1])
        self.assertEqual(history[-1]['payload']['employer_evidence'],evidence)
