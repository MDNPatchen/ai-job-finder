"""Failure-path and evidence regressions from the v3.1.27 reliability audit."""
import io,json,unittest
from datetime import date
from urllib.error import HTTPError
from unittest.mock import patch
from tracker_store import export_workspace_json,import_workspace_json,make_workspace,WorkspaceConflict
from tracker_sync import persist,merge_latest,adopt_remote
from workspace_merge import merge_workspaces
from qualification_matcher import compile_resume_profile,assess_job_qualifications
from description_quality import assess_description
from official_bulletins import enrich_priority_government_jobs
from source_http import fetch_json,request_budget
from smartrecruiters_source import fetch_board
from job_workflow import annotate_new_results


def row(name='A',notes='original'):
    return {'Company':name,'Job Title':'Manager','Status':'Applied','Notes':notes,
            'Job URL':'https://example.org/'+name}


def state():
    return {'jobs':[row()],'seen_jobs':[],'search_baseline':False,'tracker_unlocked':True,
            'tracker_revision':2,'tracker_base':make_workspace([row()])}


class PersistenceTests(unittest.TestCase):
    def test_large_export_restores(self):
        jobs=[row(str(i),'n'*3000) for i in range(1700)]
        raw=export_workspace_json(jobs,[],True).encode()
        self.assertGreater(len(raw),5_000_000)
        self.assertEqual(len(import_workspace_json(raw)['jobs']),1700)

    def test_unicode_backup_and_evidence_are_lossless(self):
        report={'id':{'company':'Example','checked_at':'2026-10-16T20:00:00+00:00','posting':{'url':'https://example.org/A'}}}
        raw=export_workspace_json([row(notes='- call résumé owner 📞')],[],True,report).encode()
        restored=import_workspace_json(raw)
        self.assertEqual(restored['jobs'][0]['Notes'],'- call résumé owner 📞')
        self.assertEqual(restored['employer_evidence'],report)

    def test_legacy_json_migrates(self):
        old={'schema_version':1,'jobs':[row()],'seen':[],'has_baseline':True}
        restored=import_workspace_json(json.dumps(old).encode())
        self.assertEqual(restored['schema_version'],2)
        self.assertEqual(restored['employer_evidence'],{})

    def test_save_failure_preserves_pending_edits(self):
        s=state();s['jobs'][0]['Notes']='edited'
        with patch('tracker_store.save_remote_workspace',side_effect=OSError):
            self.assertFalse(persist(s,'fake','test',True))
        self.assertTrue(s['tracker_dirty'])
        self.assertEqual(s['tracker_sync_status'],'failed')
        self.assertEqual(s['jobs'][0]['Notes'],'edited')
        self.assertEqual(s['tracker_revision'],2)

    def test_retry_uses_expected_revision_and_clears_dirty(self):
        s=state()
        with patch('tracker_store.save_remote_workspace',return_value=3) as save:
            self.assertTrue(persist(s,'fake','test',True))
            self.assertEqual(save.call_args.kwargs['expected_revision'],2)
        self.assertEqual(s['tracker_revision'],3)
        self.assertFalse(s['tracker_dirty'])

    def test_conflict_is_distinct_from_network_failure(self):
        s=state()
        with patch('tracker_store.save_remote_workspace',side_effect=WorkspaceConflict):
            persist(s,'fake','test',True)
        self.assertEqual(s['tracker_sync_status'],'conflict')

    def test_session_only_never_calls_database(self):
        s=state();s['tracker_unlocked']=False
        with patch('tracker_store.save_remote_workspace') as save:
            self.assertFalse(persist(s,'fake','test',True));save.assert_not_called()
        self.assertEqual(s['tracker_sync_status'],'session')

    def test_independent_edits_and_deletion_merge(self):
        base=make_workspace([row('A'),row('B')])
        local=make_workspace([row('A','edited')])
        remote=make_workspace([row('A'),row('B'),row('C')])
        merged,conflicts=merge_workspaces(base,local,remote)
        self.assertFalse(conflicts)
        self.assertEqual({r['Company']:r['Notes'] for r in merged['jobs']},{'A':'edited','C':'original'})

    def test_delete_versus_edit_requires_choice(self):
        _,conflicts=merge_workspaces(make_workspace([row()]),make_workspace([]),make_workspace([row(notes='remote')]))
        self.assertEqual(len(conflicts),1)

    def test_same_record_conflict_does_not_mutate_local(self):
        s=state();s['jobs'][0]['Notes']='local'
        remote={**make_workspace([row(notes='remote')]),'revision':3}
        with patch('tracker_store.load_remote_workspace',return_value=remote),patch('tracker_store.save_remote_workspace') as save:
            self.assertTrue(merge_latest(s,'fake','test'))
            save.assert_not_called()
        self.assertEqual(s['jobs'][0]['Notes'],'local')

    def test_merge_race_again_remains_conflict(self):
        s=state();remote={**make_workspace([row(),row('B')]),'revision':3}
        with patch('tracker_store.load_remote_workspace',return_value=remote),patch('tracker_store.save_remote_workspace',side_effect=WorkspaceConflict):
            merge_latest(s,'fake','test')
        self.assertEqual(s['tracker_sync_status'],'conflict')
        self.assertEqual(len(s['jobs']),2)

    def test_unlock_preserves_conflicting_session_edits_and_blocks_save(self):
        s=state();s['jobs'][0]['Notes']='unsaved local'
        remote={**make_workspace([row(notes='cloud')]),'revision':5}
        self.assertTrue(adopt_remote(s,remote))
        with patch('tracker_store.save_remote_workspace') as save:
            self.assertFalse(persist(s,'fake','test',True))
            save.assert_not_called()
        self.assertEqual(s['jobs'][0]['Notes'],'unsaved local')
        with patch('tracker_store.load_remote_workspace',return_value=remote),patch('tracker_store.save_remote_workspace',return_value=6):
            self.assertFalse(merge_latest(s,'fake','test','Keep cloud’s conflicting changes'))
        self.assertEqual(s['jobs'][0]['Notes'],'cloud')
        self.assertFalse(s['tracker_dirty'])

    def test_seen_history_retains_recent_search(self):
        old=[format(i,'032x') for i in range(25000)]
        results,history=annotate_new_results([{'company':'New','title':'Manager','url':'https://example.org/new'}],old,True)
        self.assertEqual(len(history),25000)
        self.assertEqual(history[-1],results[0]['posting_id'])
        self.assertTrue(results[0]['new_since_last_search'])


class EvidenceTests(unittest.TestCase):
    def test_negated_resume_does_not_earn_documented_skills(self):
        resume='I have no experience with budgeting, vendor management, logistics, or project management.'
        self.assertEqual(compile_resume_profile(resume,())['evidence'],{})
        job={'title':'Operations Manager','description':'Manage budgets, vendor management, logistics and project management. '*12}
        result=assess_job_qualifications(job,compile_resume_profile(resume,()),resume)
        self.assertLess(result['fit_index'],30)
        self.assertFalse(result['resume_matches'])

    def test_aspirations_and_courses_are_not_work_history(self):
        for text in ['Seeking a role in vendor management.','Coursework in logistics and budgeting.','Interested in project management.']:
            self.assertEqual(compile_resume_profile(text,())['evidence'],{})

    def test_affirmative_clause_survives_neighboring_negation(self):
        evidence=compile_resume_profile('No logistics experience. Managed budgets and vendor contracts.',())['evidence']
        self.assertIn('Financial & P&L leadership',evidence)
        self.assertNotIn('Distribution & logistics',evidence)

    def test_not_only_and_without_supervision_remain_positive(self):
        for text in ['Not only managed budgets but also led teams.','Managed budgets without supervision.']:
            self.assertIn('Financial & P&L leadership',compile_resume_profile(text,())['evidence'])

    def test_provider_label_does_not_make_empty_text_detailed(self):
        jobs,_=enrich_priority_government_jobs([{'title':'Manager','source':'Workable employer','description':'','url':'https://example.org/1'}],[])
        self.assertFalse(assess_description(jobs[0])['detailed'])

    def test_duties_and_requirements_distinguished(self):
        job={'description':'Lead teams and manage operations. '*20,'description_source':'Employer posting details as supplied by provider'}
        quality=assess_description(job)
        self.assertTrue(quality['detailed']);self.assertFalse(quality['requirements_section'])
        job['description']+=' Minimum qualifications: five years of related leadership.'
        self.assertTrue(assess_description(job)['requirements_section'])
        job['description_truncated']=True
        self.assertFalse(assess_description(job)['detailed'])

    def test_long_posting_evidence_after_16000_is_read(self):
        resume='Led project management.'
        job={'title':'Manager','description':('General information. '*900)+'Project management required.'}
        result=assess_job_qualifications(job,compile_resume_profile(resume,()),resume)
        self.assertTrue(any(x['area']=='Project & program management' for x in result['resume_matches']))


class NetworkTests(unittest.TestCase):
    def test_transient_failure_retries_then_succeeds(self):
        calls=[]
        def opener(req,timeout):
            calls.append(req.full_url)
            if len(calls)==1: raise HTTPError(req.full_url,503,'Unavailable',{},None)
            return io.BytesIO(b'{"ok":true}')
        self.assertTrue(fetch_json('https://example.org',opener=opener,sleep=lambda _:None)['ok'])
        self.assertEqual(len(calls),2)

    def test_permanent_http_failure_not_retried(self):
        with patch('source_http.open_response',side_effect=HTTPError('url',404,'Not found',{},None)) as req:
            with self.assertRaises(HTTPError): fetch_json('https://example.org')
            self.assertEqual(req.call_count,1)

    def test_expired_budget_stops_requests(self):
        with request_budget(0),patch('source_http.open_response') as req:
            with self.assertRaises(TimeoutError): fetch_json('https://example.org',sleep=lambda _:None)
            req.assert_not_called()

    def test_smartrecruiters_pagination_and_partial_details(self):
        today=date.today().isoformat();calls=[]
        item=lambda i:dict(id=str(i),name='Director',releasedDate=today,location={'country':'us'})
        def get(url,timeout):
            calls.append(url)
            if 'offset=0' in url:return {'content':[item(i) for i in range(100)],'totalFound':101}
            if 'offset=100' in url:return {'content':[item(100)],'totalFound':101}
            if url.endswith('/5'):raise OSError('timeout')
            return {'postingUrl':'https://example.org/'+url.rsplit('/',1)[-1],'jobAd':{'sections':{}}}
        def normalize(title,company,url,*args,**kwargs):return {'title':title,'url':url}
        result=fetch_board(('example','Example',False),get,normalize,lambda _:True,date.fromisoformat,45,max_details=101)
        self.assertEqual(len(result),100)
        self.assertEqual(result.diagnostics['pages'],2)
        self.assertEqual(result.diagnostics['failed_details'],1)
        self.assertFalse(result.diagnostics['truncated'])
        self.assertTrue(any(j['url'].endswith('/100') for j in result))

    def test_smartrecruiters_cap_is_disclosed(self):
        item={'id':'1','name':'Director','releasedDate':date.today().isoformat(),'location':{'country':'us'}}
        def get(url,timeout):return {'content':[item,dict(item,id='2')],'totalFound':2} if '?' in url else {'postingUrl':'https://example.org/1'}
        result=fetch_board(('example','Example',False),get,lambda *a,**k:{'url':a[2]},lambda _:True,date.fromisoformat,45,max_details=1)
        self.assertTrue(result.diagnostics['truncated'])
