"""Validate and stage a restore before changing session or cloud state."""
from copy import deepcopy
from tracker_store import make_workspace
from workspace_merge import row_id


def prepare_restore(current,incoming,replace=False,applications_only=False):
    current=make_workspace(current['jobs'],current['seen'],current['has_baseline'],current['employer_evidence'])
    incoming=make_workspace(incoming['jobs'],incoming['seen'],incoming['has_baseline'],incoming['employer_evidence'])
    if replace:
        result=deepcopy(current if applications_only else incoming)
        result['jobs']=deepcopy(incoming['jobs'])
        conflicts=0
    else:
        rows={row_id(row):row for row in current['jobs']}
        conflicts=sum(row_id(row) in rows and rows[row_id(row)]!=row for row in incoming['jobs'])
        for row in incoming['jobs']: rows.setdefault(row_id(row),row)
        evidence={**incoming['employer_evidence'],**current['employer_evidence']}
        conflicts+=sum(k in current['employer_evidence'] and current['employer_evidence'][k]!=v
                       for k,v in incoming['employer_evidence'].items())
        result=make_workspace(list(rows.values()),current['seen']+incoming['seen'],
            current['has_baseline'] or incoming['has_baseline'],evidence)
    return result,conflicts
