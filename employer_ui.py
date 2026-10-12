"""Compact Streamlit presentation for free, on-demand employer due diligence."""
import hashlib
import json
from pathlib import Path

import streamlit as st
from employer_checks import check_employer


@st.cache_data(ttl=14400, show_spinner=False)
def _cached_employer_check(company, source, url, government, version, sec_email, profile_json):
    profiles = json.loads(profile_json)
    return check_employer(
        {'company':company, 'source':source, 'url':url, 'government':government},
        profiles, sec_contact_email=sec_email)


def money(value):
    try:
        n=float(value)
    except (TypeError,ValueError):
        return 'Not reported'
    sign='-' if n<0 else ''
    n=abs(n)
    if n>=1_000_000_000:return sign+'$'+f'{n/1_000_000_000:,.2f}'+'B'
    if n>=1_000_000:return sign+'$'+f'{n/1_000_000:,.1f}'+'M'
    return sign+'$'+f'{n:,.0f}'


def render_evidence(report):
    st.caption('Checked ' + report['checked_at'][:16].replace('T',' ') + ' UTC')
    st.write('**Listed hiring employer:** ' + report['company'])
    st.caption('Provider: ' + report['source'] +
               ' · Posting host: ' + report['posting']['hostname'])
    st.write('**Posting source:** ' + report['posting']['status'])
    st.caption(report['posting']['detail'])
    identity=report.get('identity') or {}
    st.write('**Employer identity:** ' + identity.get('status','Not verified'))
    st.caption(identity.get('note','No independent identity evidence available.'))
    if identity.get('legal_name'):
        st.write('Legal name in registry: ' + identity['legal_name'])
        st.caption('LEI: ' + identity.get('lei','') +
                   ' · Entity registry status: ' + identity.get('status','Unspecified'))
        if identity.get('url'):
            st.markdown('[GLEIF legal entity record](' + identity['url'] + ')')
    st.write('**How long has the employer existed?**')
    age=report.get('age')
    if age:
        st.write(age['meaning'] + ': approximately ' + str(age['years']) +
                 ' years (since ' + str(age['since_year']) + ').')
        st.caption(age['note'])
        st.markdown('[Source for organization history](' + age['source_url'] + ')')
    else:
        st.caption('Not verified from available source data. The app will not guess a founding year.')
    financial=report.get('financial') or {}
    st.write('**Financial records:** ' + financial.get('status','Not verified'))
    st.caption(financial.get('note','No financial conclusion available.'))
    filer=financial.get('filer') or {}
    if filer:
        st.caption('SEC filer: ' + filer.get('entity_name','Not specified') +
                   (' · Ticker: ' + financial['ticker'] if financial.get('ticker') else ''))
        for metric in filer.get('metrics', []):
            recent=metric['recent']
            label=(metric['label']+': '+money(recent['value']) +
                   ' (fiscal year end '+recent['period_end']+
                   ', filed '+recent['filed']+')')
            if metric.get('prior'):
                previous=metric['prior']
                label+=' · prior annual '+money(previous['value'])+' ('+previous['period_end']+')'
            st.write(label)
        if filer.get('url'):
            st.markdown('[SEC company financial filing data](' + filer['url'] + ')')
    if report.get('references'):
        st.write('**Additional public evidence**')
        for item in report['references']:
            st.markdown('- ['+item['title']+']('+item['url']+')')
    st.caption(report['warning'])


def render_employer_checker(job, number, sec_email=''):
    """Show one button, only check external services if it is clicked."""
    if 'employer_checks' not in st.session_state:
        st.session_state.employer_checks={}
    identifier=hashlib.sha256(
        (str(job['company'])+'|'+str(job['source'])+'|'+str(job['url'])).encode('utf-8')
    ).hexdigest()[:24]
    if st.button('Check employer',key=f'employer_check_{number}',
                 help='Free on-demand check: job posting URL, legal identity, operating history and public financial records.'):
        location=Path(__file__).resolve().parent/'employer_profiles.json'
        try:
            raw=location.read_bytes()
            profiles=json.loads(raw)
            if profiles.get('schema_version')!=1:
                raise ValueError('Unsupported employer_profiles.json schema')
        except (OSError,ValueError,json.JSONDecodeError) as exc:
            st.warning('Employer background catalog unavailable: '+type(exc).__name__)
            raw=b'{"employers":[]}'
        version=hashlib.sha256(raw).hexdigest()[:16]
        with st.spinner('Checking job posting and public employer records…'):
            try:
                st.session_state.employer_checks[identifier]=_cached_employer_check(
                    job['company'],job['source'],job['url'],bool(job['government']),
                    version,sec_email,raw.decode('utf-8'))
            except Exception as exc:
                st.warning('Employer check unavailable: '+type(exc).__name__)
    saved=st.session_state.employer_checks.get(identifier)
    if saved:
        with st.expander('Employer background and financial evidence',expanded=True):
            render_evidence(saved)
