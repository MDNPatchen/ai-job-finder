"""Import/export and optional durable Postgres storage for one private workspace.

Without configured Streamlit secrets, use JSON/CSV backups. Streamlit local
disk and session state are NOT durable across Community Cloud deployments.
No credentials, resume text, or tracker data are saved in GitHub.
"""
import csv
from datetime import datetime, timezone
from io import StringIO
import hmac
import json
from urllib.parse import urlsplit

STATUSES=('Saved','Applied','Interviewing','Offer','Rejected','Skipped','Withdrawn')
COLUMNS=('Company','Job Title','Location','Job URL','Salary','Status',
         'Date Recorded','Interview Date','Follow-up Date','Notes')
MAX_BYTES=5_000_000
MAX_JOBS=5000
MAX_SEEN=25000


def _cell(value,limit=4000):
    return str(value or '').strip()[:limit]


def normalize_tracker_row(row):
    if not isinstance(row,dict):
        raise ValueError('Job tracker row must be an object')
    out={col:_cell(row.get(col),3000 if col=='Notes' else 800) for col in COLUMNS}
    if not out['Company'] or not out['Job Title']:
        raise ValueError('Every tracked job needs a company and title')
    if out['Status'] not in STATUSES:
        raise ValueError('Invalid application status: '+out['Status'][:80])
    url=out['Job URL']
    if url and (urlsplit(url).scheme.lower() not in ('http','https') or
                not urlsplit(url).netloc):
        raise ValueError('Job URL must use http or https')
    for field in ('Date Recorded','Interview Date','Follow-up Date'):
        if out[field]:
            try:
                datetime.strptime(out[field],'%Y-%m-%d')
            except ValueError as exc:
                raise ValueError(field+' must have format YYYY-MM-DD') from exc
    return out


def _normalize_jobs(rows):
    if not isinstance(rows,list) or len(rows)>MAX_JOBS:
        raise ValueError('Too many saved jobs in backup')
    return [normalize_tracker_row(row) for row in rows]


def import_tracker_csv(raw):
    if len(raw)>MAX_BYTES:
        raise ValueError('CSV backup exceeds 5 MB')
    text=raw.decode('utf-8-sig')
    reader=csv.DictReader(StringIO(text))
    if not reader.fieldnames or not set(COLUMNS).issubset(reader.fieldnames):
        raise ValueError('CSV is missing one or more Job Tracker columns')
    rows=[]
    for row in reader:
        if len(rows)>=MAX_JOBS:
            raise ValueError('CSV exceeds 5,000 tracked jobs')
        rows.append(normalize_tracker_row(row))
    return rows


def _excel_safe(value):
    text=str(value or '')
    if text.lstrip().startswith(('=','+','-','@')):
        return "'"+text
    return text


def export_tracker_csv(rows):
    stream=StringIO()
    writer=csv.DictWriter(stream,fieldnames=COLUMNS)
    writer.writeheader()
    for row in _normalize_jobs(rows):
        writer.writerow({col:_excel_safe(row[col]) for col in COLUMNS})
    return stream.getvalue()


def clean_seen(seen):
    if not isinstance(seen,list):
        raise ValueError('Seen-job IDs must be an array')
    if len(seen)>MAX_SEEN:
        raise ValueError('Too many seen-job IDs in backup')
    return sorted({str(x) for x in seen if isinstance(x,str)
                   and len(x)==32 and all(c in '0123456789abcdef' for c in x)})


def make_workspace(jobs=None,seen=None,has_baseline=False):
    return {'schema_version':1,'jobs':_normalize_jobs(list(jobs or [])),
            'seen':clean_seen(list(seen or [])),
            'has_baseline':bool(has_baseline)}


def export_workspace_json(jobs,seen,has_baseline):
    payload=make_workspace(jobs,seen,has_baseline)
    payload['exported_utc']=datetime.now(timezone.utc).isoformat()
    return json.dumps(payload,indent=2,ensure_ascii=False)


def import_workspace_json(raw):
    if len(raw)>MAX_BYTES:
        raise ValueError('Backup exceeds 5 MB')
    obj=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(obj,dict) or obj.get('schema_version')!=1:
        raise ValueError('Unsupported tracker backup version')
    return make_workspace(obj.get('jobs'),obj.get('seen'),obj.get('has_baseline',False))


def authenticate(password,expected):
    if not expected or len(expected)<12:
        return False
    return hmac.compare_digest(str(password).encode(),str(expected).encode())


def _connect(database_url):
    import psycopg
    return psycopg.connect(database_url,connect_timeout=8)


def load_remote_workspace(database_url,workspace_id):
    """Secret DB credentials stay on Streamlit's server; no public write API."""
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'CREATE TABLE IF NOT EXISTS ai_job_finder_workspace '
                '(workspace_id TEXT PRIMARY KEY, payload JSONB NOT NULL, '
                'updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            cur.execute(
                'SELECT payload FROM ai_job_finder_workspace WHERE workspace_id=%s',
                (workspace_id,))
            row=cur.fetchone()
            data=row[0] if row else make_workspace()
            return make_workspace(data.get('jobs'),data.get('seen'),
                                  data.get('has_baseline',False))


def save_remote_workspace(database_url,workspace_id,jobs,seen,has_baseline):
    payload=make_workspace(jobs,seen,has_baseline)
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'CREATE TABLE IF NOT EXISTS ai_job_finder_workspace '
                '(workspace_id TEXT PRIMARY KEY, payload JSONB NOT NULL, '
                'updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            cur.execute(
                'INSERT INTO ai_job_finder_workspace (workspace_id,payload) '
                'VALUES (%s,%s::jsonb) ON CONFLICT (workspace_id) DO UPDATE '
                'SET payload=EXCLUDED.payload,updated_at=CURRENT_TIMESTAMP',
                (workspace_id,json.dumps(payload)))
