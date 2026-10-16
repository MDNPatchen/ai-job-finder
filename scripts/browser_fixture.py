"""Offline browser fixture. Synthetic records only; never imported by app.py."""
import sys,runpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from build_info import MATCHING_ENGINE_VERSION
from qualification_matcher import compile_resume_profile,assess_job_qualifications
if 'browser_fixture' not in st.session_state:
    st.session_state.browser_fixture=True
    st.session_state.matching_engine_version=MATCHING_ENGINE_VERSION
    resume='Directed regional operations. Led teams, managed budgets and negotiated vendor agreements.'
    st.session_state.resume_text=resume
    profile=compile_resume_profile(resume)
    jobs=[]
    for i,title in enumerate(['Regional Operations Director','Workplace Experience Supervisor','Store Manager']):
        job=dict(title=title,company='Example Employer — browser test',location='Minneapolis, MN',government=False,
                 url=f'https://example.org/jobs/{i}',source='Greenhouse',date='2026-10-16',work_style='Hybrid',
                 description='Responsibilities: Lead teams, manage budgets and oversee regional operations. '*15,
                 description_source='Employer posting details as supplied by provider' if i!=1 else 'RSS summary only')
        job['qualification_match']=assess_job_qualifications(job,profile,resume)
        jobs.append(job)
    st.session_state.search_results=jobs
    st.session_state.search_stats=dict(run_id='BROWSERTEST',matching_version=MATCHING_ENGINE_VERSION,searched='Browser test',
        excluded=dict(old=0,undated=0,location=0),sources={'Example':3},errors=[],fetched=3,preferences={},
        board_health=[dict(board='Keyword source',provider='Fixture',status='Active',bounded_coverage=True,records=3)])
runpy.run_path(str(Path(__file__).resolve().parents[1]/'app.py'),run_name='__main__')
