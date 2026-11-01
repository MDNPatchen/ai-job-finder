"""Deterministic slow-source fixture for real-browser cancellation tests."""
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_http import check_cancelled
import time

def fixture_fetch(terms,state_filter=None,progress=None,credentials=None):
    jobs=[];health=[];counts={}
    for i in range(2):
        if i:
            for _ in range(120):
                time.sleep(.1);check_cancelled()
        jobs.append(dict(title='Operations Director '+str(i),company='Fixture Employer',
            url='https://example.org/vacancy/'+str(i),location='Minneapolis, MN',
            description='Lead teams and manage budgets. '*30,source='Greenhouse',
            date=str(date.today()),eligible=True,government=False,work_style='Hybrid',salary=''))
        health.append(dict(provider='Fixture',board='Source '+str(i),status='Active',records=1))
        counts['Source '+str(i)]=1
        if progress:progress(jobs,[],counts,health,i+1,2)
    return jobs,[],counts,health

# Swap the real network search for the fixture, then run the real app.
import runpy
import app_core
app_core.fetch_all_free_jobs=fixture_fetch
runpy.run_path(str(Path(__file__).resolve().parents[1]/'app.py'),run_name='__main__')
