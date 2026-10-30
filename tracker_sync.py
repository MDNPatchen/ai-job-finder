"""Shared persistence state and recovery UI for every page."""
from copy import deepcopy
from datetime import datetime,timezone
import streamlit as st
import tracker_store as store
from workspace_merge import merge_workspaces


def snapshot(state):
    return store.make_workspace(state.get('jobs',[]),state.get('seen_jobs',[]),
        state.get('search_baseline',False),state.get('employer_checks',{}))


def apply_workspace(state,data):
    state['jobs']=deepcopy(data['jobs'])
    state['seen_jobs']=list(data['seen'])
    state['search_baseline']=data['has_baseline']
    state['employer_checks']=deepcopy(data.get('employer_evidence',{}))
    # Restored rows must not inherit stale editor values.
    for key in list(state):
        if str(key).startswith(('notes_','follow_','status_')):
            del state[key]


def persist(state,database_url,workspace_id,enabled):
    state['tracker_dirty']=True
    if state.get('tracker_sync_status')=='conflict':
        return False
    if not enabled or not state.get('tracker_unlocked'):
        state['tracker_sync_status']='session'
        return False
    try:
        local=snapshot(state)
        revision=store.save_remote_workspace(database_url,workspace_id,local['jobs'],
            local['seen'],local['has_baseline'],expected_revision=state.get('tracker_revision',0),
            employer_evidence=local['employer_evidence'])
        state['tracker_revision']=revision
        state['tracker_base']=deepcopy(local)
        state['tracker_dirty']=False
        state['tracker_sync_status']='saved'
        state['tracker_storage_error']=''
        state['tracker_last_synced']=datetime.now(timezone.utc).isoformat()
        return True
    except store.WorkspaceConflict:
        state['tracker_sync_status']='conflict'
        state['tracker_storage_error']='Another session has newer changes'
    except Exception as exc:
        state['tracker_sync_status']='failed'
        state['tracker_storage_error']=type(exc).__name__
    return False


def merge_latest(state,database_url,workspace_id,choice=None):
    remote=store.load_remote_workspace(database_url,workspace_id)
    merged,conflicts=merge_workspaces(state.get('tracker_base',store.make_workspace()),snapshot(state),remote)
    if conflicts and choice is None:
        return conflicts
    if conflicts:
        # Resolve only records edited on both sides; retain nonconflicting changes.
        from workspace_merge import keyed_rows
        selected=snapshot(state) if choice=='Keep this session’s conflicting changes' else remote
        by_id=dict(zip(merged['job_keys'],merged['jobs']))
        selected_rows=keyed_rows(selected['jobs'])
        for conflict in conflicts:
            label,key=conflict.split(': ',1)
            target=by_id if label=='Application' else merged['employer_evidence']
            source=selected_rows if label=='Application' else selected.get('employer_evidence',{})
            if key in source: target[key]=deepcopy(source[key])
            else: target.pop(key,None)
        merged['jobs']=list(by_id.values())
    apply_workspace(state,merged)
    state['tracker_revision']=remote['revision']
    state['tracker_base']=deepcopy(remote)
    state['tracker_sync_status']='pending'
    persist(state,database_url,workspace_id,True)
    return []


def adopt_remote(state,remote):
    """Unlock must not silently discard edits made before authentication."""
    base=store.make_workspace()
    local=snapshot(state)
    merged,conflicts=merge_workspaces(base,local,remote)
    state['tracker_revision']=remote['revision']
    state['tracker_unlocked']=True
    state['tracker_loaded']=True
    if conflicts:
        state['tracker_base']=base
        state['tracker_sync_status']='conflict'
        state['tracker_storage_error']='Session edits differ from saved applications; merge before saving'
        state['tracker_dirty']=True
    else:
        apply_workspace(state,merged)
        state['tracker_base']=deepcopy(remote)
        state['tracker_sync_status']='pending'
    return conflicts


def render_sync_status(database_url,workspace_id,enabled):
    state=st.session_state
    status=state.get('tracker_sync_status','session')
    if status=='saved':
        st.caption('Saved to cloud · '+state.get('tracker_last_synced','')[:19].replace('T',' ')+' UTC')
    elif status in ('failed','conflict'):
        st.error('Cloud save incomplete. Your changes are still in this session. '+state.get('tracker_storage_error',''))
        st.download_button('Download recovery backup',store.export_workspace_json(
            state.jobs,state.seen_jobs,state.search_baseline,state.get('employer_checks',{})),
            'job_tracker_recovery.json','application/json',key='recovery_download')
        if status=='failed':
            if st.button('Retry cloud save',key='retry_cloud_save'):
                persist(state,database_url,workspace_id,enabled)
                st.rerun()
        else:
            st.caption('Merge preserves independent edits and deletions. Competing edits need your choice.')
            choice=st.selectbox('If the same application changed in both sessions',[
                'Ask before resolving conflicts','Keep cloud’s conflicting changes',
                'Keep this session’s conflicting changes'],key='conflict_choice')
            if st.button('Merge cloud changes and retry',key='merge_cloud_changes'):
                try:
                    conflicts=merge_latest(state,database_url,workspace_id,
                        None if choice.startswith('Ask') else choice)
                    if conflicts:
                        st.warning(f'{len(conflicts)} records have competing edits. Choose which version to retain, then retry. Download a recovery backup first.')
                    else: st.rerun()
                except Exception as exc: st.error('Unable to merge: '+type(exc).__name__)
    else:
        st.caption('Session-only changes · Download a backup in Job Tracker to keep them.' if state.get('tracker_dirty')
                   else 'Tracker storage: session only. Unlock cloud storage in Job Tracker or use backups.')


def render_history(database_url,workspace_id):
    with st.expander('Recover a previous cloud version'):
        st.caption('The latest 20 successful versions are retained. Download the current backup before restoring.')
        if st.button('Load recovery versions'):
            try: st.session_state['recovery_versions']=store.load_workspace_history(database_url,workspace_id)
            except Exception as exc: st.error('Recovery unavailable: '+type(exc).__name__)
        versions=st.session_state.get('recovery_versions',[])
        if versions:
            idx=st.selectbox('Saved version',range(len(versions)),format_func=lambda i:
                f"Version {versions[i]['revision']} · {versions[i]['saved_at']}")
            if st.checkbox('Replace this session with the selected saved version'):
                if st.button('Restore saved version'):
                    current=snapshot(st.session_state)
                    st.session_state.before_restore_backup=store.export_workspace_json(current['jobs'],current['seen'],
                        current['has_baseline'],current['employer_evidence'])
                    data=versions[idx]['payload']
                    apply_workspace(st.session_state,store.make_workspace(data.get('jobs'),data.get('seen'),
                        data.get('has_baseline'),data.get('employer_evidence')))
                    persist(st.session_state,database_url,workspace_id,True)
                    st.rerun()
