import csv,io,json,unittest
from threading import Event
from unittest.mock import patch
from search_task import SearchTask
from source_http import check_cancelled,ContextPool
from tracker_store import make_workspace,export_workspace_json,import_workspace_json
from tracker_sync import apply_workspace,snapshot
from workspace_recovery import prepare_restore
from match_review import review_rows,export_review,evaluate_review,sample_jobs
from source_support import with_recovery_links
from test_reliability_redesign import row

class BackgroundSearchTests(unittest.TestCase):
    def test_partial_results_and_cancellation_retain_completed_batch(self):
        ready=Event()
        def worker(task):
            task.publish({'matches':[1]},'First source done');ready.set()
            task.cancel_event.wait(2)
            with ContextPool(1) as pool:pool.submit(check_cancelled).result()
            task.publish({'matches':[2]})
        task=SearchTask(worker,'resume-A');self.assertTrue(ready.wait(2))
        self.assertTrue(task.thread.is_alive())
        snap=task.snapshot();snap['payload']['matches'].append(99)
        task.cancel();task.thread.join(2)
        self.assertFalse(task.thread.is_alive())
        self.assertEqual(task.snapshot()['status'],'cancelled')
        self.assertEqual(task.snapshot()['payload']['matches'],[1])
    def test_sessions_are_isolated_and_failure_retains_partial(self):
        def fail(task):
            task.publish({'matches':['A']});raise ValueError('unavailable')
        a=SearchTask(fail,'A');b=SearchTask(lambda t:t.publish({'matches':['B']}),'B')
        a.thread.join(2);b.thread.join(2)
        self.assertEqual(a.snapshot()['status'],'failed')
        self.assertEqual(b.snapshot()['status'],'complete')
        self.assertEqual(a.snapshot()['payload']['matches'],['A'])
        self.assertEqual(b.snapshot()['payload']['matches'],['B'])
    def test_cancelled_context_does_not_leak_to_another_search(self):
        a=SearchTask(lambda t:(t.cancel(),check_cancelled()),'A');a.thread.join(2)
        b=SearchTask(lambda t:check_cancelled(),'B');b.thread.join(2)
        self.assertEqual(b.snapshot()['status'],'complete')

class RecoveryTests(unittest.TestCase):
    def test_exact_backup_restart_restore_and_editor_invalidation(self):
        evidence={'posting':{'checked_at':'2026-10-17T10:00:00Z','identity':{'status':'verified'}}}
        original=make_workspace([row(notes='résumé 📞')],['a'*32],True,evidence)
        backup=export_workspace_json(original['jobs'],original['seen'],True,evidence)
        fresh={'notes_0':'stale','follow_0':'2020-01-01','status_0':'Rejected'}
        apply_workspace(fresh,import_workspace_json(backup.encode()))
        self.assertEqual(snapshot(fresh),original)
        self.assertNotIn('notes_0',fresh)
        self.assertNotIn('status_0',fresh)
    def test_modified_backup_rejected_before_state_change(self):
        raw=json.loads(export_workspace_json([row()],[],False));raw['jobs'][0]['Notes']='corrupt'
        with self.assertRaisesRegex(ValueError,'integrity'):import_workspace_json(json.dumps(raw).encode())
    def test_missing_or_wrong_type_jobs_cannot_erase_workspace(self):
        for value in [None,{},'bad']:
            with self.assertRaises(ValueError):import_workspace_json(json.dumps({'schema_version':2,'jobs':value}).encode())
    def test_legacy_without_checksum_still_imports(self):
        self.assertEqual(len(import_workspace_json(json.dumps({'schema_version':1,'jobs':[row()]}).encode())['jobs']),1)
    def test_merge_preserves_current_competing_records_and_counts(self):
        a=make_workspace([row(notes='current')],['a'*32],True,{'x':{'value':1}})
        b=make_workspace([row(notes='old'),row('B')],['b'*32],False,{'x':{'value':2}})
        merged,conflicts=prepare_restore(a,b)
        self.assertEqual(conflicts,2);self.assertEqual(len(merged['jobs']),2)
        self.assertEqual(merged['jobs'][0]['Notes'],'current')
        self.assertEqual(merged['employer_evidence']['x']['value'],1)
        replacement,_=prepare_restore(a,b,replace=True)
        self.assertEqual(replacement,b);self.assertEqual(a['jobs'][0]['Notes'],'current')
    def test_csv_replace_preserves_history_and_employer_evidence(self):
        a=make_workspace([row()],['a'*32],True,{'x':{'value':1}})
        result,_=prepare_restore(a,make_workspace([row('B')]),True,True)
        self.assertEqual(result['seen'],a['seen']);self.assertEqual(result['employer_evidence'],a['employer_evidence'])

class MatchReviewTests(unittest.TestCase):
    def jobs(self):
        return [{'title':'Director '+str(i),'company':'Example','url':'https://example.org/'+str(i),
                 'qualification_match':{'fit_index':80,'resume_present':True}} for i in range(100)]
    def test_sample_spans_first_twenty_and_tail_without_duplicates(self):
        sample=sample_jobs(self.jobs());self.assertEqual(len(sample),40)
        ranks=[r for r,_ in sample];self.assertEqual(ranks[:20],list(range(1,21)))
        self.assertEqual(ranks[-1],100);self.assertEqual(len(set(ranks)),40)
    def test_blank_review_has_no_invented_accuracy(self):
        rows=review_rows(self.jobs(),'resume','run')
        result=evaluate_review(export_review(rows).encode(),rows)
        self.assertIsNone(result['suitable_share_of_decided']);self.assertEqual(result['decided'],0)
    def test_only_decided_labels_count_and_mismatched_run_fails(self):
        rows=review_rows(self.jobs(),'resume','run')
        rows[0]['Your judgment']='Suitable';rows[1]['Your judgment']='Unsuitable';rows[2]['Your judgment']='Uncertain'
        result=evaluate_review(export_review(rows).encode(),rows)
        self.assertEqual(result['suitable_share_of_decided'],50)
        wrong=review_rows(self.jobs(),'different resume','run')
        with self.assertRaises(ValueError):evaluate_review(export_review(rows).encode(),wrong)
    def test_unavailable_routes_do_not_become_success(self):
        item=with_recovery_links([{'board':'Bold Business','status':'Failed'}])[0]
        self.assertEqual(item['status'],'Failed');self.assertTrue(item['recovery_url'].startswith('https://'))

class ResumeReviewRegressions(unittest.TestCase):
    def test_civil_pe_requirement_and_affirmative_resume_evidence(self):
        from posting_requirements import extract_posting_requirements
        job={'title':'Project Manager - Public Works (PE)','description':'Who You Are\nLicensed Civil PE in Washington with 10+ years of experience in public works design.'}
        checks=extract_posting_requirements(job,'Business Administration graduate. Directed operations.')
        match=next(x for x in checks['checks'] if x['area']=='Engineering professional license')
        self.assertGreater(match['ranking_caution'],0)
        negative=extract_posting_requirements(job,'I am not a licensed civil PE.')
        self.assertGreater(next(x for x in negative['checks'] if x['area']=='Engineering professional license')['ranking_caution'],0)
        checks=extract_posting_requirements(job,'Licensed Civil PE in Washington. Designed public infrastructure.')
        self.assertEqual(next(x for x in checks['checks'] if x['area']=='Engineering professional license')['ranking_caution'],0)
    def test_post_hire_city_residency_is_flagged_without_disqualification(self):
        from posting_requirements import extract_posting_requirements
        checks=extract_posting_requirements({'title':'Director','description':'The successful candidate must be a city of Philadelphia resident within six months of hire.'},'')
        item=next(x for x in checks['checks'] if x['area']=='Employer residency condition')
        self.assertEqual(item['ranking_caution'],0)
        self.assertIn('post-hire',item['priority'])
    def test_dotted_it_title_is_not_generic_project_management(self):
        from career_fit_guardrails import evaluate_career_fit
        result=evaluate_career_fit({'title':'I.T. Project Manager','description':'Manage software deployments.'},'Led publishing operations.')
        self.assertGreater(result['penalty'],0)
    def test_clinic_management_minimum_is_not_generic_leadership(self):
        from posting_requirements import extract_posting_requirements
        job={'title':'Group Facility Administrator','description':'Qualifications\n3+ years’ direct management experience of a healthcare clinic or center(s) required.'}
        result=extract_posting_requirements(job,'Directed newspaper operations and budgets.')
        self.assertGreater(next(x for x in result['checks'] if x['area']=='Healthcare clinic management experience')['ranking_caution'],0)
    def test_long_graduate_degree_substitution_is_not_mandatory(self):
        from qualification_matcher import compile_resume_profile,assess_job_qualifications
        text="Qualifications:\nBachelor's degree required.\nSubstitution:\nPossession of a graduate degree (Master's degree or higher) from an accredited college or university with major coursework in specialized subject matter areas such as public or business administration, management, business law, contract law, public policy, urban studies, economics, statistical analysis, finance, accounting or other fields of study closely related to the essential functions of positions in the Class series may be substituted for one (1) year of required experience."
        resume='Bachelor of Business Administration. Led operations.'
        q=assess_job_qualifications({'title':'Senior Project Manager','description':text},compile_resume_profile(resume),resume)
        masters=[x for x in q['posting_requirement_checks'] if x['area']=='Master degree']
        self.assertTrue(masters);self.assertTrue(all(x['ranking_caution']==0 for x in masters))
    def test_public_trust_bundle_retains_certificate_and_hostname_checks(self):
        import ssl
        from source_http import trusted_context
        context=trusted_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
