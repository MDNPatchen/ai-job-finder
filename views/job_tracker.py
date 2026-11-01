"""Job Tracker page."""
from app_core import *  # noqa: F401,F403  shared helpers, constants and Streamlit
from app_core import _secret


def render():
    st.markdown(hero('Job Tracker'),unsafe_allow_html=True)

    if tracker_cloud_enabled():
        if st.session_state.tracker_unlocked:
            st.caption('Private cloud tracker unlocked.')
            tracker_sync.render_history(_secret('TRACKER_DATABASE_URL'),
                _secret('TRACKER_WORKSPACE_ID') or 'personal')
        else:
            with st.form('tracker_unlock'):
                entered_password=st.text_input('Private tracker password',type='password',
                   help='Configured in Streamlit Secrets, never stored in GitHub.')
                unlock=st.form_submit_button('Unlock saved applications')
                if unlock:
                    try:
                        if unlock_tracker_workspace(entered_password):
                            st.success('Private applications loaded.')
                            st.rerun()
                        else:
                            from tracker_store import unlock_throttle
                            wait=unlock_throttle.seconds_remaining()
                            st.error(f'Too many incorrect attempts. Try again in {wait} seconds.' if wait
                                     else 'Incorrect password or password configuration.')
                    except Exception as exc:
                        st.error('Could not load cloud tracker: '+type(exc).__name__)
            st.warning('Not unlocked: edits are session-only. Unlock before searching to '
                       'retain job history across devices or deployments.')
    else:
        st.caption('Session-only storage · Download a backup to preserve changes.')
    if st.session_state.get('tracker_storage_error'):
        st.error('Cloud save failed ('+st.session_state.tracker_storage_error+
                 '). Export a JSON backup now; the latest changes are in this session.')

    # Keep application follow-ups visible without navigating away from the tracker.
    active_rows=[j for j in st.session_state.jobs if j.get('Status') not in
                 ('Skipped','Rejected','Withdrawn')]
    status_counts=Counter(str(j.get('Status') or 'Not started') for j in active_rows)
    st.markdown('<div class="job-module-heading">Application pipeline</div>',
                unsafe_allow_html=True)
    pc1,pc2,pc3=st.columns(3)
    pc1.metric('Active openings',len(active_rows))
    pc2.metric('Applications sent / progressing',sum(
        v for k,v in status_counts.items()
        if any(term in k.lower() for term in
               ('appl','interview','offer','screen','follow-up'))))
    pc3.metric('Interview stage',sum(v for k,v in status_counts.items()
                if 'interview' in k.lower()))

    st.markdown('<div class="job-module-heading">Tracker backup and restore</div>',unsafe_allow_html=True)
    backup_left,backup_right=st.columns(2)
    with backup_left:
        download_file_widget(
            'Download tracker backup JSON',
            export_workspace_json(st.session_state.jobs,st.session_state.seen_jobs,
                                  st.session_state.search_baseline,st.session_state.get('employer_checks',{}),
                                  tracker_sync.snapshot(st.session_state)['profile']),
            'job_tracker_full_backup.json','application/json',
            'tracker_full_backup')
    with backup_right:
        download_file_widget(
            'Download applications CSV',
            export_tracker_csv(st.session_state.jobs),
            'job_tracker.csv','text/csv','tracker_applications_csv')
        st.caption('CSV is spreadsheet-safe. Use JSON for exact restoration, history and employer evidence.')
    if st.session_state.get('restore_notice'):
        st.info(st.session_state.restore_notice)
    if st.session_state.get('before_restore_backup'):
        download_file_widget('Download backup from before restore',st.session_state.before_restore_backup,
            'before_restore.json','application/json','before_restore_download')
    with st.expander('Restore applications and job history'):
        uploaded_backup=st.file_uploader('Choose prior Job Tracker CSV or full JSON backup',
                                         type=['csv','json'],key='tracker_restore_file')
        restore_mode=st.radio('Import behavior',[
            'Merge with existing applications','Replace existing applications'],
            help='Replacing JSON also replaces seen-job history. CSV backups contain applications only.')
        if st.button('Restore selected backup',disabled=uploaded_backup is None):
            try:
                raw=uploaded_backup.getvalue()
                if uploaded_backup.name.lower().endswith('.json'):
                    incoming=import_workspace_json(raw)
                    restored_jobs=incoming['jobs']
                else:
                    restored_jobs=import_tracker_csv(raw)
                    incoming=None
                current=tracker_sync.snapshot(st.session_state)
                staged,conflicts=prepare_restore(current,incoming if incoming is not None else make_workspace(restored_jobs),
                    replace=restore_mode.startswith('Replace'),applications_only=incoming is None)
                st.session_state.before_restore_backup=export_workspace_json(current['jobs'],current['seen'],
                    current['has_baseline'],current['employer_evidence'],current['profile'])
                tracker_sync.apply_workspace(st.session_state,staged)
                st.session_state.restore_notice=f"Restored {len(restored_jobs)} applications. {conflicts} competing records kept from this session."
                synced=persist_tracker_if_unlocked()
                if tracker_cloud_enabled() and st.session_state.tracker_unlocked and not synced:
                    st.warning('Imported into this session, but cloud save failed. Keep a backup.')
                else:
                    st.success(f'Restored {len(restored_jobs)} saved applications.')
                st.rerun()
            except (UnicodeDecodeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                st.error('Backup not imported: '+str(exc)[:280])

    with st.expander('Add a job', expanded=False):
        with st.form('add_job'):
            company=st.text_input('Company')
            title=st.text_input('Job Title')
            location=st.text_input('Location')
            url=st.text_input('Job Posting URL')
            salary=st.text_input('Salary / Range')
            status=st.selectbox('Status',STATUSES)
            recorded=st.date_input('Date Recorded',value=date.today())
            interview=st.date_input('Interview Date (optional)',value=None)
            follow_up=st.date_input('Follow-up Date (optional)',value=None)
            notes=st.text_area('Notes / Next Steps')
            if st.form_submit_button('Save Job'):
                if company.strip() and title.strip():
                    try:
                        row={'Company':company.strip(),'Job Title':title.strip(),
                             'Location':location.strip(),'Job URL':url.strip(),
                             'Salary':salary.strip(),'Status':status,
                             'Date Recorded':str(recorded),
                             'Interview Date':str(interview) if interview else '',
                             'Follow-up Date':str(follow_up) if follow_up else '',
                             'Notes':notes.strip()}
                        from tracker_store import normalize_tracker_row
                        row=normalize_tracker_row(row)
                        identity=posting_id({'company':row['Company'],'title':row['Job Title'],
                                             'location':row['Location'],'url':row['Job URL']})
                        existing={posting_id({'company':x['Company'],'title':x['Job Title'],
                                              'location':x['Location'],'url':x['Job URL']})
                                  for x in st.session_state.jobs}
                        if identity in existing:
                            st.info('This vacancy is already in your tracker.')
                        else:
                            st.session_state.jobs.append(row)
                            persist_tracker_if_unlocked()
                            st.success('Job added.')
                            st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                else:
                    st.warning('Company and Job Title are required.')

    jobs=st.session_state.jobs
    if jobs:
        st.metric('Applications tracked',len(jobs))
        selected_status=st.selectbox('Filter by status',['All']+STATUSES)
        visible=[j for j in jobs if selected_status=='All' or j['Status']==selected_status]
        st.dataframe(pd.DataFrame(visible),use_container_width=True,hide_index=True)
        idx=st.selectbox('Update a job',range(len(jobs)),
                         format_func=lambda i:f"{jobs[i]['Company']} — {jobs[i]['Job Title']}")
        job=jobs[idx]
        for report in st.session_state.get('employer_checks',{}).values():
            if report.get('company')==job['Company'] and (report.get('posting') or {}).get('url')==job['Job URL']:
                with st.expander('Saved employer evidence'):
                    from employer_ui import render_evidence
                    render_evidence(report)
                    st.caption('Evidence is a dated snapshot. Recheck the original posting before applying.')
        new_status=st.selectbox('New status',STATUSES,index=STATUSES.index(job['Status']),key=f'status_{idx}')
        new_notes=st.text_area('Update notes',value=job['Notes'],key=f'notes_{idx}')
        prior_follow=job.get('Follow-up Date','')
        try:
            follow_value=date.fromisoformat(prior_follow) if prior_follow else None
        except ValueError:
            follow_value=None
        new_follow=st.date_input('Next follow-up',value=follow_value,key=f'follow_{idx}')
        if st.button('Save Changes'):
            jobs[idx]['Status']=new_status
            jobs[idx]['Notes']=new_notes.strip()[:3000]
            jobs[idx]['Follow-up Date']=str(new_follow) if new_follow else ''
            persist_tracker_if_unlocked()
            st.success('Changes saved'+(' to cloud.' if st.session_state.tracker_unlocked
                                         and not st.session_state.get('tracker_storage_error')
                                         else ' for this session.'))
            st.rerun()
        if st.checkbox('Enable deletion of selected job',value=False):
            if st.button('Delete selected job'):
                jobs.pop(idx)
                persist_tracker_if_unlocked()
                st.success('Selected job deleted.')
                st.rerun()
    else:
        st.info('No jobs tracked yet. Save an opening from Find Jobs or import a prior backup.')
