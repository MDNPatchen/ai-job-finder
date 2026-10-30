"""Three-way workspace merge: preserve concurrent edits, including deletions."""
from copy import deepcopy
from job_workflow import posting_id


def row_id(row):
    return posting_id({'company':row.get('Company'), 'title':row.get('Job Title'),
                       'url':row.get('Job URL'), 'location':row.get('Location')})


def keyed_rows(rows):
    """Map rows to unique keys. Repeated identities get an occurrence suffix
    so duplicate rows (e.g. from a CSV import) are never silently collapsed."""
    keyed,seen={},{}
    for row in rows:
        base_id=row_id(row)
        seen[base_id]=seen.get(base_id,0)+1
        key=base_id if seen[base_id]==1 else f'{base_id}#{seen[base_id]}'
        keyed[key]=row
    return keyed


def merge_workspaces(base, local, remote):
    """Conflicts are explicit; never choose silently between competing edits."""
    conflicts=[]
    def merge_map(before, ours, theirs, label):
        merged={}
        for key in dict.fromkeys([*theirs,*ours,*before]):
            b,l,r=before.get(key),ours.get(key),theirs.get(key)
            if l==b: value=r
            elif r==b or l==r: value=l
            else:
                conflicts.append(f'{label}: {key}')
                continue
            if value is not None: merged[key]=deepcopy(value)
        return merged
    maps=[keyed_rows(w.get('jobs',[])) for w in (base,local,remote)]
    jobs=merge_map(*maps,'Application')
    evidence=merge_map(*(w.get('employer_evidence',{}) for w in (base,local,remote)), 'Employer check')
    return {'jobs':list(jobs.values()),'job_keys':list(jobs),
            'seen':list(dict.fromkeys(remote.get('seen',[])+local.get('seen',[])))[-25000:],
            'has_baseline':bool(local.get('has_baseline') or remote.get('has_baseline')),
            'employer_evidence':evidence}, conflicts
