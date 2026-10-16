"""Three-way workspace merge: preserve concurrent edits, including deletions."""
from copy import deepcopy
from job_workflow import posting_id


def row_id(row):
    return posting_id({'company':row.get('Company'), 'title':row.get('Job Title'),
                       'url':row.get('Job URL'), 'location':row.get('Location')})


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
    maps=[{row_id(r):r for r in w.get('jobs',[])} for w in (base,local,remote)]
    jobs=merge_map(*maps,'Application')
    evidence=merge_map(*(w.get('employer_evidence',{}) for w in (base,local,remote)), 'Employer check')
    return {'jobs':list(jobs.values()),
            'seen':list(dict.fromkeys(remote.get('seen',[])+local.get('seen',[])))[-25000:],
            'has_baseline':bool(local.get('has_baseline') or remote.get('has_baseline')),
            'employer_evidence':evidence}, conflicts
