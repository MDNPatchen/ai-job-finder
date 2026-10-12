import re
from io import BytesIO
from datetime import date
import streamlit as st
import fitz
from docx import Document
import pandas as pd

st.set_page_config(page_title='AI Job Finder', page_icon='💼', layout='wide')

SKILLS = ['Leadership','Strategic Planning','Marketing','Data Analysis','Logistics','Compliance','Project Management','Operations Management','Budget Management','P&L Management','Advertising Sales','Digital Strategy','Audience Development','Community Relations','Business Development','Team Management','Revenue Growth','Financial Planning','Change Management','Circulation','Editorial Leadership','Sales Management','Vendor Management']
TITLES = ['Group Newspaper Publisher','Group Publisher','Newspaper Publisher','Publisher','Operations Director','Director of Operations','General Manager','Regional Manager','Operations Manager','Project Manager','Sales Director','Vice President']
STATUSES = ['Saved','Applied','Interviewing','Offer','Rejected','Skipped','Withdrawn']
PUBLISHER_AREAS = ['Multi-publication or multi-site leadership','Revenue, profitability, and P&L oversight','Advertising and sales leadership','Digital publishing and subscriptions','Editorial and cross-functional leadership','Budgeting, forecasting, and financial planning','Audience growth and marketing','Community and advertiser partnerships','Circulation, distribution, and logistics','Talent development and organizational change']

for key, default in {'jobs': [], 'resume_text': '', 'confirmed_titles': [], 'analysis': None, 'approved_suggestions': []}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def extract_resume_text(file):
    data = file.getvalue()
    name = file.name.lower()
    if name.endswith('.pdf'):
        with fitz.open(stream=data, filetype='pdf') as doc:
            return '\n'.join(page.get_text() for page in doc)
    if name.endswith('.docx'):
        doc = Document(BytesIO(data))
        lines = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    lines.append(cell.text)
        return '\n'.join(lines)
    if name.endswith('.txt'):
        return data.decode('utf-8-sig', errors='replace')
    return ''


def keyword_matches(text, options):
    return [item for item in options if re.search(r'\b' + re.escape(item) + r'\b', text, re.I)]


# A local, transparent reference library. These are examples of common publisher
# responsibilities, not assertions about the user's actual experience.
COMPETENCIES = [
    ('Financial & P&L leadership', ['profitability', 'profit and loss', 'p&l', 'budget', 'forecast', 'cash flow', 'financial performance'], 'Financial leadership', 'Regional General Manager'),
    ('Multi-site business leadership', ['multiple newspapers', 'multiple publications', 'group publisher', 'group newspaper publisher', 'multi-site', 'multi-location', 'regional operations'], 'Multi-location leadership', 'Regional Operations Director'),
    ('Advertising & sales leadership', ['advertising', 'ad sales', 'sales team', 'sales director', 'sales revenue', 'account executives'], 'Commercial leadership', 'Director of Sales'),
    ('Digital transformation', ['digital revenue', 'digital marketing', 'online advertising', 'digital subscription', 'digital strategy', 'website'], 'Digital business growth', 'Digital Strategy Director'),
    ('Editorial & cross-functional leadership', ['editorial', 'managing editor', 'newsroom', 'editor', 'cross-functional'], 'Cross-functional management', 'General Manager'),
    ('Audience & marketing development', ['circulation', 'audience', 'subscriber', 'subscription', 'marketing', 'readership'], 'Customer growth', 'Marketing Director'),
    ('Distribution & logistics', ['distribution', 'delivery', 'route', 'logistics', 'circulation director'], 'Operations optimization', 'Distribution Director'),
    ('Talent & organizational change', ['recruit', 'hiring', 'training', 'cross-training', 'reorganization', 'staff development', 'employee'], 'People leadership', 'Director of Operations'),
    ('Community partnerships', ['community', 'chamber', 'partnership', 'advertiser relationships', 'stakeholder'], 'Stakeholder relations', 'Community Relations Director'),
    ('Negotiation & vendor management', ['negotiat', 'vendor', 'contract', 'supplier', 'insurance premium'], 'Negotiation', 'Procurement Director'),
]


def analyze_locally(resume):
    lines = [line.strip() for line in resume.splitlines() if line.strip()]
    documented, verify, roles, suggestions = [], [], {}, []
    for skill, phrases, transferable, role in COMPETENCIES:
        evidence = []
        for line in lines:
            if any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', line, re.I) for term in phrases):
                evidence.append(line[:350])
            if len(evidence) == 2:
                break
        if evidence:
            documented.append({'skill': skill, 'evidence': evidence, 'transferable': transferable})
            roles.setdefault(role, []).append(transferable)
            suggestions.append({'skill': skill, 'source': evidence[0],
                'wording': f'Experience in {transferable.lower()}: {evidence[0]}',
                'note': 'Draft based on resume wording; edit for accuracy before using.'})
        else:
            verify.append(skill)
    return {'documented': documented, 'verify': verify, 'roles': roles, 'suggestions': suggestions}

# Career matches use the same publisher competency evidence as Career Analysis.
# Scores are transparent overlap indicators, not employment eligibility predictions.
CAREER_PATHS = [
    {'title': 'Regional Operations Director', 'industry': 'Multi-location businesses', 'core': ['Multi-site business leadership', 'Financial & P&L leadership', 'Talent & organizational change'], 'additional': ['Distribution & logistics', 'Negotiation & vendor management'], 'focus': 'Emphasize locations led, budgets, operational improvements and team size.'},
    {'title': 'General Manager', 'industry': 'Services, media, retail and local businesses', 'core': ['Financial & P&L leadership', 'Advertising & sales leadership', 'Talent & organizational change'], 'additional': ['Multi-site business leadership', 'Community partnerships'], 'focus': 'Highlight overall business ownership, revenue, profitability and leadership results.'},
    {'title': 'Director of Business Development', 'industry': 'Business services and B2B organizations', 'core': ['Advertising & sales leadership', 'Community partnerships', 'Financial & P&L leadership'], 'additional': ['Audience & marketing development', 'Negotiation & vendor management'], 'focus': 'Show account growth, partnerships, pricing strategy and measurable sales outcomes.'},
    {'title': 'Director of Marketing', 'industry': 'Marketing, media and consumer services', 'core': ['Audience & marketing development', 'Digital transformation', 'Advertising & sales leadership'], 'additional': ['Community partnerships', 'Financial & P&L leadership'], 'focus': 'Show audience growth, campaign results, digital revenue and customer acquisition.'},
    {'title': 'Distribution Operations Director', 'industry': 'Logistics and delivery services', 'core': ['Distribution & logistics', 'Talent & organizational change', 'Financial & P&L leadership'], 'additional': ['Multi-site business leadership', 'Negotiation & vendor management'], 'focus': 'Show delivery efficiencies, route changes, service levels and cost savings.'},
    {'title': 'Director of Community Partnerships', 'industry': 'Nonprofits, education and civic organizations', 'core': ['Community partnerships', 'Talent & organizational change', 'Audience & marketing development'], 'additional': ['Advertising & sales leadership', 'Financial & P&L leadership'], 'focus': 'Describe stakeholder relationships, public-facing leadership and partnership outcomes.'},
    {'title': 'Digital Business Director', 'industry': 'Digital media and subscription businesses', 'core': ['Digital transformation', 'Audience & marketing development', 'Financial & P&L leadership'], 'additional': ['Advertising & sales leadership', 'Editorial & cross-functional leadership'], 'focus': 'Show digital product initiatives, subscription or advertising growth, and cross-team execution.'},
    {'title': 'Chief Operating Officer (smaller organization)', 'industry': 'Small and midsize organizations', 'core': ['Financial & P&L leadership', 'Multi-site business leadership', 'Talent & organizational change'], 'additional': ['Negotiation & vendor management', 'Advertising & sales leadership'], 'focus': 'Document executive decision-making, business scale, direct reports and financial accountability.'},
]


def get_career_matches(resume):
    analysis = analyze_locally(resume)
    evidence_by_skill = {item['skill']: item['evidence'] for item in analysis['documented']}
    results = []
    for path in CAREER_PATHS:
        all_skills = path['core'] + path['additional']
        matched = [skill for skill in all_skills if skill in evidence_by_skill]
        unconfirmed = [skill for skill in all_skills if skill not in evidence_by_skill]
        # Core requirements count twice as much as additional competencies.
        total_weight = 2 * len(path['core']) + len(path['additional'])
        matched_weight = sum(2 if skill in path['core'] else 1 for skill in matched)
        score = round(100 * matched_weight / total_weight)
        results.append({**path, 'score': score, 'matched': matched,
                        'unconfirmed': unconfirmed, 'evidence': evidence_by_skill})
    return sorted(results, key=lambda x: (-x['score'], x['title']))


st.sidebar.title('💼 AI Job Finder')
page = st.sidebar.radio('Navigation', ['Dashboard','My Resume','Career Analysis','Career Matches','Find Jobs','Job Tracker'])
st.sidebar.caption('Free local resume comparison. No API key or AI usage charges.')

if page == 'Dashboard':
    st.title('📊 Job Search Dashboard')
    jobs = st.session_state.jobs
    a, b, c = st.columns(3)
    a.metric('Tracked Jobs', len(jobs))
    b.metric('Applied', sum(j['Status'] == 'Applied' for j in jobs))
    c.metric('Interviewing', sum(j['Status'] == 'Interviewing' for j in jobs))
    a, b, c = st.columns(3)
    a.metric('Offers', sum(j['Status'] == 'Offer' for j in jobs))
    b.metric('Saved', sum(j['Status'] == 'Saved' for j in jobs))
    c.metric('Skipped', sum(j['Status'] == 'Skipped' for j in jobs))
    if jobs:
        st.dataframe(pd.DataFrame(jobs), use_container_width=True, hide_index=True)
    else:
        st.info('Go to Job Tracker to add a job.')
    st.caption('Jobs are stored only for this session. Export your CSV to keep a backup.')

elif page == 'My Resume':
    st.title('📄 My Resume')
    file = st.file_uploader('Upload PDF, Word, or TXT resume', type=['pdf','docx','txt'])
    if file:
        try:
            extracted = extract_resume_text(file)
            if extracted.strip():
                if extracted != st.session_state.resume_text:
                    st.session_state.resume_text = extracted
                    st.session_state.analysis = None
                    st.session_state.pop('career_matches', None)
                    st.session_state.approved_suggestions = []
                st.success('Resume uploaded successfully!')
            else:
                st.warning('No readable text was found. Scanned PDFs may need OCR.')
        except Exception as exc:
            st.error(f'Unable to read file: {exc}')
    text = st.session_state.resume_text
    if text:
        with st.expander('View extracted resume text'):
            st.text_area('Resume text', text, height=280)
        st.subheader('Skills mentioned in your resume')
        matches = keyword_matches(text, SKILLS)
        st.write(', '.join(matches) if matches else 'No matches from the starter list.')
        st.caption('These are keyword matches, not verified skill assessments.')
        st.subheader('Confirm your actual job titles')
        found = keyword_matches(text, TITLES)
        if not st.session_state.confirmed_titles:
            st.session_state.confirmed_titles = ['Group Newspaper Publisher']
        choices = list(dict.fromkeys(found + st.session_state.confirmed_titles))
        selected = st.multiselect('Recognized or previously confirmed titles', choices, default=[t for t in st.session_state.confirmed_titles if t in choices])
        additional = st.text_input('Add other actual titles (comma-separated)')
        confirmed = list(dict.fromkeys(selected + [x.strip() for x in additional.split(',') if x.strip()]))
        st.session_state.confirmed_titles = confirmed
        st.write('**Confirmed titles:**', ', '.join(confirmed) if confirmed else 'None yet')
        st.info('Next, open Career Analysis to compare your experience against publisher responsibilities.')
    else:
        st.info('Upload a resume to begin.')

elif page == 'Career Analysis':
    st.title('🧭 Publisher Competency & Transferable Skills')
    st.write('Free, local comparison of your resume with common Group Newspaper Publisher responsibilities. Nothing is sent to an AI service.')
    actual_title = st.text_input('Your actual position', value='Group Newspaper Publisher')
    st.caption('Your real job title stays separate from transferable job categories.')
    if not st.session_state.resume_text:
        st.warning('First upload your resume on the My Resume page.')
    else:
        if st.button('Analyze My Resume', type='primary'):
            st.session_state.analysis = analyze_locally(st.session_state.resume_text)
            st.session_state.approved_suggestions = []
            st.success('Comparison complete. Review each result for accuracy.')
        analysis = st.session_state.analysis
        if analysis:
            st.subheader('Possible documented strengths')
            st.caption('A matching phrase is a clue, not proof you performed the duty. Review the source text.')
            for item in analysis['documented']:
                with st.expander(item['skill'], expanded=False):
                    st.write('**Resume text that matched:**')
                    for line in item['evidence']:
                        st.write(line)
                    st.write('**Transferable area:**', item['transferable'])
            st.subheader('Publisher responsibilities to confirm')
            st.write('These areas were not detected by our phrase list. That does not mean you lack the experience.')
            for area in analysis['verify']:
                st.write('• ' + area)
            st.subheader('Potential related career paths')
            for role, skills in analysis['roles'].items():
                st.write(f'**{role}** — related experience: {", ".join(skills)}')
            st.caption('These are ideas for exploration, not eligibility or job-match guarantees.')
            st.subheader('Resume wording suggestions — your approval required')
            st.write('These are editable starting points, not finished resume bullets.')
            approved = []
            for i, item in enumerate(analysis['suggestions']):
                st.markdown(f'**{i + 1}. {item["skill"]}**')
                st.caption('Original evidence: ' + item['source'])
                wording = st.text_area('Edit suggested wording', value=item['wording'], key=f'suggestion_{i}')
                if st.checkbox('Approve this wording', key=f'approve_{i}') and wording.strip():
                    approved.append(wording.strip())
            st.session_state.approved_suggestions = approved
            if approved:
                st.download_button('⬇️ Download approved wording', '\n\n'.join(approved), 'approved_resume_suggestions.txt', 'text/plain')
            st.info('Nothing is added to your resume automatically. You approve and download only the wording you want.')

elif page == 'Career Matches':
    st.title('🎯 Transferable Career Matches')
    st.write('Explore career paths outside newspaper publishing based on the responsibilities actually mentioned in your resume.')
    st.info('Free, local phrase-based matching. These are exploratory comparisons, not job openings, hiring predictions or professional qualifications assessments.')
    if not st.session_state.resume_text.strip():
        st.warning('First upload your resume on the My Resume page.')
    else:
        st.write('**Actual career background:** ' + (', '.join(st.session_state.confirmed_titles) or 'Group Newspaper Publisher'))
        st.caption('Your real title is not changed to match another industry.')
        if st.button('Compare My Career Skills', type='primary'):
            st.session_state.career_matches = get_career_matches(st.session_state.resume_text)
        if 'career_matches' in st.session_state:
            results = st.session_state.career_matches
            industry_options = ['All industries'] + sorted({r['industry'] for r in results})
            industry = st.selectbox('Filter by industry', industry_options)
            visible = [r for r in results if industry == 'All industries' or r['industry'] == industry]
            st.caption('Overlap scores measure how many weighted phrases were found in your resume. A low score can mean missing wording, not missing ability.')
            for r in visible:
                with st.expander(f"{r['title']} — {r['score']}% documented competency overlap", expanded=False):
                    st.write('**Industry:**', r['industry'])
                    st.progress(r['score'] / 100)
                    st.write('**Skills supported by resume phrases:**')
                    if r['matched']:
                        for skill in r['matched']:
                            st.markdown('**' + skill + '**')
                            st.caption('Resume evidence: ' + ' | '.join(r['evidence'][skill][:2]))
                    else:
                        st.write('None from this starter competency list.')
                    st.write('**Responsibilities to confirm or document:**')
                    if r['unconfirmed']:
                        for skill in r['unconfirmed']:
                            st.write('• ' + skill)
                    else:
                        st.write('All mapped areas had phrase matches; verify that the duties were actually performed.')
                    st.write('**Resume tailoring idea:**', r['focus'])
                    st.caption('Only add achievements, responsibilities and numbers you can substantiate. Use Career Analysis to edit and approve suggested wording.')
            st.download_button('⬇️ Export Career Matches CSV',
                pd.DataFrame([{'Career':r['title'], 'Industry':r['industry'],
                    'Documented overlap (%)':r['score'],
                    'Matched areas':'; '.join(r['matched']),
                    'Areas to verify':'; '.join(r['unconfirmed']),
                    'Resume focus':r['focus']} for r in visible]).to_csv(index=False),
                'career_matches.csv', 'text/csv')

elif page == 'Find Jobs':
    st.title('🔎 Find Jobs')
    st.text_input('Job title or keywords', placeholder='Regional Director')
    st.text_input('Location', placeholder='Rochester, MN or Remote')
    if st.button('Search Jobs'):
        st.info('Live job search is not connected yet.')

elif page == 'Job Tracker':
    st.title('📋 Job Application Tracker')
    with st.expander('➕ Add a New Job', expanded=True):
        with st.form('add_job'):
            company = st.text_input('Company')
            title = st.text_input('Job Title')
            location = st.text_input('Location')
            url = st.text_input('Job Posting URL')
            salary = st.text_input('Salary / Range')
            status = st.selectbox('Status', STATUSES)
            recorded = st.date_input('Date Recorded', value=date.today())
            interview = st.date_input('Interview Date (optional)', value=None)
            notes = st.text_area('Notes / Next Steps')
            if st.form_submit_button('Save Job'):
                if company.strip() and title.strip():
                    st.session_state.jobs.append({'Company':company.strip(),'Job Title':title.strip(),'Location':location.strip(),'Job URL':url.strip(),'Salary':salary.strip(),'Status':status,'Date Recorded':str(recorded),'Interview Date':str(interview) if interview else '', 'Notes':notes.strip()})
                    st.success('Job added.')
                else:
                    st.warning('Company and Job Title are required.')
    jobs = st.session_state.jobs
    if jobs:
        selected_status = st.selectbox('Filter by status', ['All'] + STATUSES)
        visible = [j for j in jobs if selected_status == 'All' or j['Status'] == selected_status]
        st.dataframe(pd.DataFrame(visible), use_container_width=True, hide_index=True)
        idx = st.selectbox('Update a job', range(len(jobs)), format_func=lambda i: f"{jobs[i]['Company']} — {jobs[i]['Job Title']}")
        job = jobs[idx]
        new_status = st.selectbox('New status', STATUSES, index=STATUSES.index(job['Status']))
        new_notes = st.text_area('Update notes', value=job['Notes'], key=f'notes_{idx}')
        if st.button('Save Changes'):
            jobs[idx]['Status'] = new_status
            jobs[idx]['Notes'] = new_notes
            st.success('Changes saved for this session.')
            st.rerun()
        st.download_button('⬇️ Export Job Tracker CSV', pd.DataFrame(jobs).to_csv(index=False), 'job_tracker.csv', 'text/csv')
    else:
        st.info('No jobs tracked yet.')
    st.warning('Tracker data is temporary. Export a CSV backup before closing your session. Permanent storage is a future step.')
