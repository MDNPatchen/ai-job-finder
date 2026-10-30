"""Import/export and optional durable Postgres storage for one private workspace.

Without configured Streamlit secrets, use JSON/CSV backups. Streamlit local
disk and session state are NOT durable across Community Cloud deployments.
No credentials, resume text, or tracker data are saved in GitHub.
"""
import csv
import hashlib
from datetime import datetime, timezone
from io import StringIO
import hmac
import json
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit

STATUSES=('Saved','Applied','Interviewing','Offer','Rejected','Skipped','Withdrawn')
COLUMNS=('Company','Job Title','Location','Job URL','Salary','Status',
         'Date Recorded','Interview Date','Follow-up Date','Notes')
MAX_BYTES=256_000_000
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
        raise ValueError('CSV backup exceeds 256 MB')
    try:
        text=raw.decode('utf-8-sig')
        reader=csv.DictReader(StringIO(text))
        if not reader.fieldnames or not (set(COLUMNS)-{'Follow-up Date'}).issubset(reader.fieldnames):
            raise ValueError('CSV is missing one or more Job Tracker columns')
        rows=[]
        for row in reader:
            if len(rows)>=MAX_JOBS:
                raise ValueError('CSV exceeds 5,000 tracked jobs')
            rows.append(normalize_tracker_row(row))
        return rows

    except csv.Error as exc:
        raise ValueError('Invalid or oversized CSV field') from exc


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
    return list(dict.fromkeys(x for x in seen if isinstance(x,str)
                   and len(x)==32 and all(c in '0123456789abcdef' for c in x)))[-MAX_SEEN:]


def clean_evidence(evidence):
    if not isinstance(evidence,dict) or len(evidence)>1000:
        raise ValueError('Employer evidence must contain at most 1,000 checks')
    if len(json.dumps(evidence,ensure_ascii=False).encode())>5_000_000:
        raise ValueError('Employer evidence exceeds 5 MB')
    for key,report in evidence.items():
        if not isinstance(key,str) or not isinstance(report,dict):
            raise ValueError('Invalid employer evidence')
    return evidence


def make_workspace(jobs=None,seen=None,has_baseline=False,employer_evidence=None):
    return {'schema_version':2,'jobs':_normalize_jobs(list(jobs or [])),
            'seen':clean_seen(list(seen or [])),
            'has_baseline':bool(has_baseline),
            'employer_evidence':clean_evidence(employer_evidence or {})}


def export_workspace_json(jobs,seen,has_baseline,employer_evidence=None):
    payload=make_workspace(jobs,seen,has_baseline,employer_evidence)
    payload['integrity_sha256']=workspace_digest(payload)
    payload['exported_utc']=datetime.now(timezone.utc).isoformat()
    text=json.dumps(payload,indent=2,ensure_ascii=False)
    if len(text.encode('utf-8'))>MAX_BYTES:
        raise ValueError('Workspace exceeds the supported 256 MB backup size')
    return text


def workspace_digest(payload):
    fields={key:payload.get(key) for key in ('schema_version','jobs','seen','has_baseline','employer_evidence')}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def import_workspace_json(raw):
    if len(raw)>MAX_BYTES:
        raise ValueError('Backup exceeds 256 MB')
    obj=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(obj,dict) or obj.get('schema_version') not in (1,2):
        raise ValueError('Unsupported tracker backup version')
    if not isinstance(obj.get('jobs'),list) or not isinstance(obj.get('seen',[]),list):
        raise ValueError('Backup must contain an applications array and valid history')
    if not isinstance(obj.get('has_baseline',False),bool):
        raise ValueError('Invalid search history flag')
    if 'integrity_sha256' in obj and obj['integrity_sha256']!=workspace_digest(obj):
        raise ValueError('Backup integrity check failed; file may be incomplete or modified')
    return make_workspace(obj.get('jobs'),obj.get('seen'),obj.get('has_baseline',False),
                          obj.get('employer_evidence'))


def authenticate(password,expected):
    if not expected or len(expected)<12:
        return False
    return hmac.compare_digest(str(password).encode(),str(expected).encode())


class UnlockThrottle:
    """Slow down password guessing. Shared by every session in this server
    process, so opening a new browser tab does not reset the count."""
    def __init__(self,max_failures=5,lockout_seconds=60,clock=monotonic):
        self.max_failures=max_failures;self.lockout_seconds=lockout_seconds
        self.clock=clock;self.failures=0;self.locked_until=0.0;self._lock=Lock()

    def seconds_remaining(self):
        with self._lock:
            return max(0,int(self.locked_until-self.clock()+0.999))

    def record(self,success):
        with self._lock:
            if success:
                self.failures=0;self.locked_until=0.0
                return
            self.failures+=1
            if self.failures>=self.max_failures:
                # Each further failure while over the limit restarts the lockout.
                self.locked_until=self.clock()+self.lockout_seconds


unlock_throttle=UnlockThrottle()


class WorkspaceConflict(RuntimeError):
    """Another session changed this workspace; reload/merge before saving."""


def _connect(database_url):
    import psycopg
    return psycopg.connect(database_url,connect_timeout=8,
                           options='-c statement_timeout=10000 -c lock_timeout=5000')


_schema_ready=set()
_schema_lock=Lock()


def _schema(cur,database_url=None):
    # DDL (especially ALTER TABLE) takes a brief exclusive table lock, so run it
    # once per database per server process rather than on every load and save.
    key=hashlib.sha256(str(database_url).encode()).hexdigest() if database_url else None
    if key is not None and key in _schema_ready:
        return
    cur.execute('CREATE TABLE IF NOT EXISTS ai_job_finder_workspace '
                '(workspace_id TEXT PRIMARY KEY, payload JSONB NOT NULL, '
                'revision BIGINT NOT NULL DEFAULT 0, '
                'updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    cur.execute('ALTER TABLE ai_job_finder_workspace ADD COLUMN IF NOT EXISTS '
                'revision BIGINT NOT NULL DEFAULT 0')
    cur.execute('CREATE TABLE IF NOT EXISTS ai_job_finder_history '
                '(workspace_id TEXT NOT NULL, revision BIGINT NOT NULL, '
                'payload JSONB NOT NULL, saved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, '
                'PRIMARY KEY (workspace_id,revision))')
    # Commit the idempotent DDL on its own so a later rollback (for example a
    # save conflict) cannot undo tables this process already marked as ready.
    cur.connection.commit()
    if key is not None:
        with _schema_lock: _schema_ready.add(key)


def load_remote_workspace(database_url,workspace_id):
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            _schema(cur,database_url)
            cur.execute('SELECT payload,revision,updated_at FROM ai_job_finder_workspace '
                        'WHERE workspace_id=%s',(workspace_id,))
            row=cur.fetchone()
    data=row[0] if row else make_workspace()
    result=make_workspace(data.get('jobs'),data.get('seen'),data.get('has_baseline',False),
                          data.get('employer_evidence'))
    result['revision']=row[1] if row else 0
    result['updated_at']=row[2].isoformat() if row else None
    return result


def save_remote_workspace(database_url,workspace_id,jobs,seen,has_baseline,
                          *,expected_revision,employer_evidence=None):
    """Atomic compare-and-swap. Stale clients never overwrite a newer payload."""
    payload=make_workspace(jobs,seen,has_baseline,employer_evidence)
    encoded=json.dumps(payload)
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            _schema(cur,database_url)
            # Preserve legacy revision 0 before the first upgrade save.
            cur.execute('INSERT INTO ai_job_finder_history (workspace_id,revision,payload) '
                        'SELECT workspace_id,revision,payload FROM ai_job_finder_workspace '
                        'WHERE workspace_id=%s ON CONFLICT DO NOTHING',(workspace_id,))
            cur.execute('INSERT INTO ai_job_finder_workspace (workspace_id,payload,revision) '
                        'SELECT %s,%s::jsonb,1 WHERE %s=0 '
                        'ON CONFLICT (workspace_id) DO UPDATE SET payload=%s::jsonb, '
                        'revision=ai_job_finder_workspace.revision+1,updated_at=CURRENT_TIMESTAMP '
                        'WHERE ai_job_finder_workspace.revision=%s RETURNING revision',
                        (workspace_id,encoded,expected_revision,encoded,expected_revision))
            row=cur.fetchone()
            # INSERT SELECT cannot reach an existing row when expected_revision>0.
            if row is None and expected_revision>0:
                cur.execute('UPDATE ai_job_finder_workspace SET payload=%s::jsonb, '
                            'revision=revision+1,updated_at=CURRENT_TIMESTAMP '
                            'WHERE workspace_id=%s AND revision=%s RETURNING revision',
                            (encoded,workspace_id,expected_revision))
                row=cur.fetchone()
            if row is None:
                raise WorkspaceConflict('Cloud workspace changed in another session')
            revision=row[0]
            cur.execute('INSERT INTO ai_job_finder_history (workspace_id,revision,payload) '
                        'VALUES (%s,%s,%s::jsonb)',(workspace_id,revision,encoded))
            cur.execute('DELETE FROM ai_job_finder_history WHERE workspace_id=%s AND revision '
                        'NOT IN (SELECT revision FROM ai_job_finder_history WHERE workspace_id=%s '
                        'ORDER BY revision DESC LIMIT 20)',(workspace_id,workspace_id))
    return revision


def load_workspace_history(database_url,workspace_id):
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            _schema(cur,database_url)
            cur.execute('SELECT revision,saved_at,payload FROM ai_job_finder_history '
                        'WHERE workspace_id=%s ORDER BY revision DESC LIMIT 20',(workspace_id,))
            return [{'revision':r[0],'saved_at':r[1].isoformat(),'payload':r[2]} for r in cur.fetchall()]


def upcoming_followups(jobs, today, days=7):
    """Return active due actions, retaining row indices for duplicate titles."""
    from datetime import date, timedelta
    actions = []
    for index, job in enumerate(jobs):
        if job.get('Status') not in ('Saved', 'Applied', 'Interviewing', 'Offer'):
            continue
        try:
            due = date.fromisoformat(job.get('Follow-up Date') or '')
        except (ValueError, TypeError):
            continue
        if due <= today + timedelta(days=days):
            actions.append((due, index, job))
    return sorted(actions, key=lambda action: (action[0], action[1]))


def complete_followup(jobs, index):
    """Clear a completed reminder without changing application status or notes."""
    jobs[index]['Follow-up Date'] = ''
