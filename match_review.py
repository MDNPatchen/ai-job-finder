"""A repeatable user-reviewed sample; never invent human labels or accuracy."""
import csv,hashlib,json
from io import StringIO
from job_workflow import posting_id
from ranked_breakdowns import evidence_index
from tracker_store import _excel_safe

FIELDS=('Sample ID','Run ID','Resume fingerprint','Rank','Company','Title','URL','Fit index',
        'Resume evidence','Requirements to verify','Posting text','Your judgment','Review notes')


def sample_jobs(jobs,limit=40):
    if len(jobs)<=limit:return list(enumerate(jobs,1))
    top=limit//2
    indices=list(range(top))
    rest=limit-top
    indices += [top+round(i*(len(jobs)-top-1)/(rest-1)) for i in range(rest)]
    return [(i+1,jobs[i]) for i in indices]


def review_rows(jobs,resume,run_id):
    fingerprint=hashlib.sha256(resume.encode()).hexdigest()[:16]
    rows=[]
    for rank,job in sample_jobs(jobs):
        q=job.get('qualification_match') or {}
        rows.append(dict(zip(FIELDS,(
            posting_id(job),run_id,fingerprint,rank,job.get('company',''),job.get('title',''),job.get('url',''),
            evidence_index(q),json.dumps(q.get('resume_matches',[]),ensure_ascii=False),
            json.dumps({k:q.get(k,[]) for k in ('not_documented','posting_requirement_checks','career_fit_cautions')},ensure_ascii=False),
            job.get('description',''),'',''))))
    return rows


def export_review(rows):
    text=StringIO();writer=csv.DictWriter(text,fieldnames=FIELDS);writer.writeheader()
    for row in rows:writer.writerow({k:_excel_safe(row[k]) for k in FIELDS})
    return text.getvalue()


def evaluate_review(raw,expected):
    if len(raw)>10_000_000:raise ValueError('Review file exceeds 10 MB')
    csv.field_size_limit(1_000_000)
    reader=csv.DictReader(StringIO(raw.decode('utf-8-sig')))
    if not set(FIELDS).issubset(reader.fieldnames or []):raise ValueError('Missing review columns')
    originals={r['Sample ID']:r for r in expected};seen=set();counts={'Suitable':0,'Unsuitable':0,'Uncertain':0,'Unreviewed':0}
    high_total=high_unsuitable=0
    for row in reader:
        key=row.get('Sample ID')
        if key not in originals or key in seen:raise ValueError('Unknown or repeated sample ID')
        seen.add(key);original=originals[key]
        for field in ('Run ID','Resume fingerprint','Rank','Fit index','URL'):
            if str(row.get(field))!=str(original[field]):raise ValueError('Review belongs to a different search or its reference fields changed')
        judgment=(row.get('Your judgment') or '').strip() or 'Unreviewed'
        if judgment not in counts:raise ValueError('Use Suitable, Unsuitable, Uncertain, or leave the judgment blank')
        counts[judgment]+=1
        if judgment in ('Suitable','Unsuitable') and float(original['Fit index'])>=75:
            high_total+=1;high_unsuitable+=judgment=='Unsuitable'
    if seen!=set(originals):raise ValueError('Review must retain every sample row')
    decided=counts['Suitable']+counts['Unsuitable']
    return {'sample_size':len(originals),'judgments':counts,'decided':decided,
        'suitable_share_of_decided':round(100*counts['Suitable']/decided,1) if decided else None,
        'high_fit_reviewed':high_total,'high_fit_unsuitable':high_unsuitable,
        'interpretation':'User judgments on a stratified sample; not overall accuracy or hiring probability'}
