"""Read-only CSV invariants. Passing checks does not prove job suitability."""
import csv
import math
from collections import Counter
from pathlib import Path

FIT='Comparative fit index (0-96; not hiring probability)'
PRIORITY='Leadership review priority (not fit score)'


def audit_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        fields=reader.fieldnames or []
        rows=list(reader)
    findings=[]
    def check(name,passed,detail):
        findings.append(dict(check=name,status='pass' if passed else 'fail',detail=detail))
    required=['Rank',FIT,'Job URL','Job title','Matching engine version','Search run ID (UTC)','Review order']
    missing=[name for name in required if name not in fields]
    check('Required columns',not missing,'Missing: '+', '.join(missing) if missing else 'All present')
    check('Nonempty export',bool(rows),f'{len(rows)} rows')
    if missing or not rows: return dict(rows=len(rows),findings=findings,passed=False)
    check('Complete row structure',all(None not in row and all(v is not None for v in row.values()) for row in rows),'No shifted or incomplete CSV rows')
    check('Sequential ranks',[r['Rank'] for r in rows]==[str(i) for i in range(1,len(rows)+1)],'Ranks must be 1 through row count')
    urls=[r['Job URL'] for r in rows]
    check('Unique posting URLs',len(set(urls))==len(urls),f'{len(urls)-len(set(urls))} duplicate URLs')
    check('Posting identifiers',all(r['Job title'].strip() and r['Job URL'].startswith(('https://','http://')) for r in rows),'Every row needs a title and web URL')
    for key in ['Matching engine version','Search run ID (UTC)','Review order']:
        values={r[key] for r in rows}
        check('Consistent '+key,len(values)==1 and bool(next(iter(values)).strip()),f'{len(values)} distinct values')
    try: scores=[float(r[FIT]) for r in rows]
    except (ValueError,TypeError): scores=[]
    valid=len(scores)==len(rows) and all(math.isfinite(v) and 0<=v<=96 for v in scores)
    check('Valid fit scores',valid,'Finite scores from 0 through 96')
    mode=rows[0]['Review order']
    if mode=='Highest fit index':
        check('Selected review order',valid and scores==sorted(scores,reverse=True),'Fit scores descend')
    elif mode=='Leadership priorities':
        columns=[PRIORITY,'Role-level review adjustment','Description review adjustment']
        if not all(c in fields for c in columns):
            findings.append(dict(check='Selected review order',status='unverified',detail='Older export omits review-priority adjustments; use v3.2.2 or later for independent reconciliation'))
        else:
            try:
                priorities=[float(r[PRIORITY]) for r in rows]
                consistent=valid and all(math.isfinite(v) for v in priorities) and all(
                    abs(scores[i]-float(r[columns[1]])-float(r[columns[2]])-priorities[i])<.011
                    and float(r[columns[1]]) in (0,8,12,18) and float(r[columns[2]]) in (0,15)
                    for i,r in enumerate(rows))
            except (ValueError,TypeError): priorities=[];consistent=False
            check('Review-priority reconciliation',consistent,'Priority equals fit minus disclosed adjustments')
            check('Selected review order',consistent and priorities==sorted(priorities,reverse=True),'Review priority descends; fit scores may differ')
    else: check('Selected review order',False,'Unknown review order')
    return dict(rows=len(rows),findings=findings,passed=all(x['status']=='pass' for x in findings),
                description_quality=dict(Counter(r.get('Job-description completeness','Unknown') for r in rows)))
