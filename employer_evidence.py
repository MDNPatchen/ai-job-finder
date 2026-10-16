"""Join only saved checks for the exact posting; never infer verification."""
import hashlib
from datetime import datetime,timezone


def evidence_key(job):
    return hashlib.sha256((str(job.get('company',''))+'|'+str(job.get('source',''))+'|'+str(job.get('url',''))).encode('utf-8')).hexdigest()[:24]


def attach_saved_evidence(jobs,checks,now=None):
    now=now or datetime.now(timezone.utc)
    result=[]
    for job in jobs:
        report=checks.get(evidence_key(job)) or {}
        checked=report.get('checked_at','')
        try:
            age=(now-datetime.fromisoformat(checked)).total_seconds()
            freshness='Current (within 24 hours)' if 0<=age<=86400 else 'Stale or invalid date — recheck'
        except (ValueError,TypeError):
            freshness='Undated — recheck' if report else 'Not checked'
        identity=report.get('identity') or {}
        posting=report.get('posting') or {}
        result.append(dict(job,employer_evidence_summary={
            'checked_at':checked,'freshness':freshness,
            'identity_status':identity.get('status','Not checked'),
            'posting_status':posting.get('status','Not checked'),
            'vacancy_status':posting.get('vacancy_status','Open status not established')}))
    return result
