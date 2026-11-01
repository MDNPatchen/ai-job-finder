"""Find Jobs page."""
from app_core import *  # noqa: F401,F403  shared helpers, constants and Streamlit
from app_core import _secret


def render():
    st.markdown(hero('Find Jobs','Nationwide · 45-day listings'),unsafe_allow_html=True)
    if st.session_state.pop('matching_engine_reset', False):
        st.caption('Search again for updated rankings.')

    state_choices = ['All states'] + [f'{name} ({code})' for code,name in sorted(US_STATES.items(),key=lambda kv:kv[1])]
    state_names=[f'{code} — {name}' for code,name in sorted(US_STATES.items())]
    WORK_OPTIONS=['On-site + Hybrid','On-site only','Hybrid only']
    SCOPE_OPTIONS=['Direct employers only (recommended)',
                   'Include recruiter listings with direct job links',
                   'All sources (including directory links)']
    EMPLOYER_SCOPE_OPTIONS=['All matching jobs (recommended)',
                            'Compact results: up to 3 per employer (10 Mayo Clinic)']
    SENIORITY_OPTIONS=['Executive / VP','Publisher','Director','Manager','Other']
    LEVEL_OPTIONS=list(MINIMUM_LEVELS)
    FILTER_OPTIONS={'f_state':state_choices,'f_work':WORK_OPTIONS,'f_scope':SCOPE_OPTIONS,
                    'f_employer_scope':EMPLOYER_SCOPE_OPTIONS,'f_include':state_names,
                    'f_exclude':state_names,'f_seniority':SENIORITY_OPTIONS,'f_min_level':LEVEL_OPTIONS}
    st.markdown('<div class="job-module-heading">Search filters</div>',unsafe_allow_html=True)
    saved_list=st.session_state.get('saved_searches') or []
    notice=st.session_state.pop('saved_search_notice',None)
    if notice:
        st.success(notice)
    if 'saved_search_select' in st.session_state:
        # Select the search just saved; set before the picker is drawn.
        st.session_state.saved_search_pick=st.session_state.pop('saved_search_select')
    if saved_list:
        pick_col,run_col,del_col=st.columns([3,1,1],vertical_alignment='bottom')
        with pick_col:
            picked=st.selectbox('Saved searches',[x['name'] for x in saved_list],key='saved_search_pick')
        chosen_saved=next(x for x in saved_list if x['name']==picked)
        with run_col:
            if st.button('Run',key='run_saved_search_button',type='primary',use_container_width=True):
                saved_searches.apply(st.session_state,chosen_saved['filters'],FILTER_OPTIONS)
                st.session_state.run_saved_search=True
                st.rerun()
        with del_col:
            if st.button('Delete',key='delete_saved_search_button',use_container_width=True):
                st.session_state.saved_searches=saved_searches.remove(saved_list,picked)
                persist_tracker_if_unlocked()
                st.rerun()
    with st.form('clean_search'):
        search_text = st.text_input('Search',placeholder='Job title, keyword or agency',
            help='Leave blank for transferable career matches.',key='f_search')
        col_state, col_type = st.columns([2,1])
        with col_state:
            chosen_state=st.selectbox('State',state_choices,key='f_state')
        with col_type:
            chosen_work=st.selectbox('Work style',WORK_OPTIONS,key='f_work',
                help='On-site + Hybrid includes fully remote Mayo Clinic and verified government jobs; fully remote private-sector positions remain excluded. On-site only and Hybrid only are strict. Unknown arrangements require verification.')
        chosen_listing_scope=st.selectbox(
            'Employer type', SCOPE_OPTIONS, key='f_scope',
            help='Recommended: employer-specific career boards and public agencies, with a link to an individual vacancy. Recruiting intermediaries, aggregators and general career directories are hidden. This does not prove the vacancy remains open; check the original employer listing.')
        min_level=st.selectbox('Minimum role level',LEVEL_OPTIONS,key='f_min_level',
            help='Manager and above hides coordinator, specialist, analyst and assistant roles. '
                 'Director and above also hides manager roles. Titles that do not state a level are kept.')
        chosen_employer_scope=st.selectbox(
            'Results per employer', EMPLOYER_SCOPE_OPTIONS, key='f_employer_scope',
            help='The full view keeps all qualifying jobs in resume-match order. The compact view hides additional jobs from employers with many postings; the count hidden is shown in diagnostics.')
        with st.expander('More filters'):
            include_states=st.multiselect(
                'Only these states (leave blank for nationwide)',state_names,key='f_include',
                help='You can pick several states instead of filtering down to one.')
            exclude_states=st.multiselect('Exclude states',state_names,key='f_exclude')
            desired_seniority=st.multiselect('Role level',SENIORITY_OPTIONS,key='f_seniority',
                help='Leave empty to include all role levels.')
            minimum_salary=st.number_input('Minimum listed annual salary ($)',
                min_value=0,max_value=500000,step=10000,key='f_minsal',
                **({} if 'f_minsal' in st.session_state else {'value':0}),
                help='Only explicitly annual salary figures are compared. This is not a salary estimate.')
            include_unknown_pay=st.checkbox(
                'Include jobs that do not disclose annual compensation',key='f_unknownpay',
                **({} if 'f_unknownpay' in st.session_state else {'value':True}))
            verified_work=st.checkbox(
                'Exclude listings with unspecified on-site/hybrid arrangements',key='f_verified',
                help='This excludes unknown arrangements but allows explicitly remote Mayo Clinic and verified government jobs.')
        submitted=st.form_submit_button('Search',type='primary',use_container_width=True)
        save_col,save_btn_col=st.columns([3,1],vertical_alignment='bottom')
        with save_col:
            save_name=st.text_input('Save these filters as',placeholder='e.g. Communications · ND, MN, SD',
                                    key='f_save_name')
        with save_btn_col:
            save_clicked=st.form_submit_button('Save this search',use_container_width=True)

    if save_clicked:
        try:
            st.session_state.saved_searches=saved_searches.upsert(
                st.session_state.get('saved_searches') or [],save_name,
                saved_searches.capture(st.session_state))
            stored=persist_tracker_if_unlocked()
            st.session_state.saved_search_notice=(f'Saved "{save_name.strip()}"'+(
                ' to your cloud tracker.' if stored else
                ' for this session. Unlock the Job Tracker to keep it.'))
            st.session_state.saved_search_select=st.session_state.saved_searches[0]['name']
            st.rerun()  # redraw so the new search appears in the Saved searches menu
        except ValueError as exc:
            st.warning(str(exc))
    if st.session_state.pop('run_saved_search',False):
        submitted=True

    if submitted:
        running=st.session_state.get('active_search')
        if running and running.snapshot(False)['status']=='running':
            st.info('A search is already running. Stop it before starting another.')
        else:
            code = chosen_state.rsplit('(',1)[-1].rstrip(')') if chosen_state!='All states' else None
            preferences={
                'included_states':[x.split(' ',1)[0] for x in include_states],
                'excluded_states':[x.split(' ',1)[0] for x in exclude_states],
                'seniority':desired_seniority,
                'minimum_level':min_level,
                'minimum_salary':minimum_salary,
                'include_unlisted_salary':include_unknown_pay,
                'verified_workplace_only':verified_work,
            }
            settings={'code':code,'work':chosen_work,'query':search_text,
                'resume':st.session_state.resume_text,'confirmed':tuple(sorted(verified_competencies())),
                'excluded':tuple(sorted(excluded_competencies())),
                'family_readiness':({f['label']:f['score'] for f in rank_families(resume_grades())}
                                    if st.session_state.resume_text.strip() else {}),
                'employer_cap':3 if chosen_employer_scope.startswith('Compact') else None,
                'preferences':preferences,'listing_scope':chosen_listing_scope,
                'scope':chosen_state,'employer_scope':chosen_employer_scope,
                'credentials':(_secret('USAJOBS_API_KEY'),_secret('USAJOBS_EMAIL'))}
            st.session_state.active_search=SearchTask(
                lambda task, captured=deepcopy(settings): run_search_task(task,captured),search_fingerprint())
            st.session_state.search_task_revision=-1
            st.session_state.search_page=0
            st.rerun()

    if 'search_results' not in st.session_state:
        st.caption('Search to find current openings. Leave the keyword blank for career matches.')
    else:
        all_results=st.session_state.search_results
        stats=st.session_state.search_stats
        if stats.get('search_status') in ('running','cancelled','failed'):
            st.caption('Partial search results · coverage and rankings may change as more sources finish.')
        for severity,message in coverage_messages(stats.get('board_health',[])):
            getattr(st,severity)(message)
        if stats.get('errors') and not stats.get('board_health'):
            st.warning('Source errors were recorded. See source coverage for details.')
        st.caption('Results are a snapshot. Provider JSON may be cached for up to 15 minutes; confirm availability on the original posting.')
        # Use the same deduplicated, filtered jobs for all three metrics.
        government_total=sum(1 for job in all_results if job['government'])
        private_total=len(all_results)-government_total
        new_count=sum(x.get('new_since_last_search',False) for x in all_results)
        st.markdown('<div class="job-module-heading">02 / Search overview</div>',unsafe_allow_html=True)
        m1,m2,m3,m4=st.columns(4)
        m1.metric('Total jobs',len(all_results))
        m2.metric('Government',government_total)
        m3.metric('Private',private_total)
        m4.metric('New',new_count)
        st.caption('Matching v'+stats.get('matching_version','')+
                   ' · '+stats.get('searched',''))
        screened=stats['excluded']
        if any(screened.get(k,0) for k in ('recruiter','directory_link','indirect_source','foreign_location')):
            st.info(f"Listing screening removed {screened.get('recruiter',0)} recruiting-firm posts, "
                    f"{screened.get('directory_link',0)} directory-only links, "
                    f"{screened.get('indirect_source',0)} third-party aggregator posts, "
                    f"and {screened.get('foreign_location',0)} explicitly non-U.S. locations. "
                    'Change Listing sources and search again to see a broader selection.')
        st.caption('Employer-named career boards and vacancy-specific URLs do not guarantee a job is still open. Verify the original employer or government posting before applying.')
        bulletin=stats.get('bulletin_diagnostics') or {}
        if bulletin.get('attempted'):
            st.caption(f"Official government bulletin lookup: {bulletin.get('full_bulletins',0)} full descriptions retrieved from {bulletin['attempted']} attempts. {bulletin.get('summary_only',0)} government listings still have summary-only job text and conservative confidence caps.")
        level=(stats.get('preferences') or {}).get('minimum_level')
        if level and level!='All levels' and stats['excluded'].get('preferences',0):
            st.caption(f"{stats['excluded']['preferences']} jobs hidden by your role level and other filters "
                       f"({level}). Choose All levels to see them.")
        if stats['excluded'].get('employer_limit',0):
            st.caption(f"{stats['excluded']['employer_limit']} more jobs hidden by employer limit.")
        if not st.session_state.resume_text.strip():
            st.info('For a detailed match review of each vacancy, upload a resume on My Resume and search again.')
        if not all_results:
            st.warning('No recent openings matched those choices. Try All states, On-site + Hybrid, or a different keyword. Strict work-arrangement filters require explicit employer labels.')
        else:
            if st.session_state.resume_text.strip():
                # Default is strict best-to-worst by the fit score shown on each card,
                # so the top match is always first.
                review_order=st.selectbox('Sort results by',
                    ['Highest fit index','Leadership priorities'],key='review_order')
                all_results=order_for_review(all_results,review_order)
                if review_order=='Highest fit index':
                    st.caption('Best match first, by the fit index shown on each listing.')
                else:
                    st.caption('Leadership priorities moves director/executive roles up: management and specialist titles '
                        'are lowered 8–18 points and incomplete descriptions 15 points for ordering only, so listings may '
                        'not appear in fit-index order. Displayed fit scores are unchanged.')
            # Export controls are no longer hidden behind résumé upload.
            # The fragment keeps data stable when the user clicks Download.
            ranked_exports(all_results,stats.get('run_id',''))
            if st.session_state.resume_text.strip() and stats.get('search_status','complete')=='complete':
                with st.expander('Review match quality'):
                    st.caption('Review up to 40 jobs: the first 20 plus a spread across the remaining results. Read requirements and resume evidence, then enter Suitable, Unsuitable, or Uncertain in Your judgment. Keep all rows and reference fields.')
                    sample=review_rows(all_results,st.session_state.resume_text,stats.get('run_id',''))
                    st.download_button('Download match review sample',export_review(sample),
                        'match_review_'+stats.get('run_id','')+'.csv','text/csv',key='match_review_download')
                    reviewed=st.file_uploader('Load completed match review',type=['csv'],key='match_review_upload')
                    if reviewed:
                        try:
                            evaluation=evaluate_review(reviewed.getvalue(),sample)
                            st.write(evaluation)
                            st.download_button('Download review results',json.dumps(evaluation,indent=2),
                                'match_review_results.json','application/json')
                        except (ValueError,UnicodeDecodeError,csv.Error) as exc:
                            st.error('Review not accepted: '+str(exc))

            st.markdown('<div class="job-module-heading">03 / Job listings</div>',unsafe_allow_html=True)
            new_only=st.checkbox('Show only new positions since the previous search',
                                 value=False,key='new_jobs_only')
            hide_tracked=st.checkbox('Hide positions already in my Job Tracker',
                                     value=False,key='hide_tracked_jobs')
            view_a,view_b=st.columns(2)
            with view_a:
                workplace_view=st.selectbox('Workplace evidence',[
                    'All arrangements','Verified on-site or hybrid',
                    'Government or Mayo remote allowed','Needs workplace confirmation'
                ],key='workplace_review_filter')
            with view_b:
                career_view=st.selectbox('Career level',[
                    'All career levels','Director / executive / publisher',
                    'Management / related roles','Other roles'
                ],key='career_review_filter')
            OTHER_FAMILY='Other matching roles'
            family_view=st.multiselect('Role family',[*ROLE_FAMILY_LABELS,OTHER_FAMILY],
                default=[*ROLE_FAMILY_LABELS,OTHER_FAMILY],key='role_family_filter',
                help='Fields where publisher experience transfers. My Resume shows how ready you are for each.')
            description_view=st.checkbox('Show detailed descriptions only',
                value=False,key='full_description_filter',
                help='Shows provider posting details and official full bulletins. Excludes summaries, unverified RSS text and unknown provenance.')
            tracked_ids={posting_id({'company':item['Company'],'title':item['Job Title'],
                       'url':item['Job URL'],'location':item['Location']})
                         for item in st.session_state.jobs}
            def review_visible(job):
                style=job.get('work_style') or 'Not specified'
                if workplace_view=='Verified on-site or hybrid' and style not in ('On-site','Hybrid'):
                    return False
                if workplace_view=='Government or Mayo remote allowed' and style!='Remote':
                    return False
                if workplace_view=='Needs workplace confirmation' and style!='Not specified':
                    return False
                if career_view!='All career levels' and career_review_category(job.get('title'))!=career_view:
                    return False
                if description_view and not has_detailed_description(job):
                    return False
                family=family_for_title(job.get('title'))
                if (family['label'] if family else OTHER_FAMILY) not in family_view:
                    return False
                return True
            display_results=[job for job in all_results
                 if (not new_only or job.get('new_since_last_search'))
                 and (not hide_tracked or posting_id(job) not in tracked_ids)
                 and review_visible(job)]
            PAGE_SIZE=12
            page_no=st.session_state.get('search_page',0)
            page_total=max(1,(len(display_results)+PAGE_SIZE-1)//PAGE_SIZE)
            page_no=min(max(page_no,0),page_total-1)
            st.session_state.search_page=page_no
            if not display_results:
                st.info('No positions match these display choices. Try turning off New only or Hide tracked.')
            else:
                st.caption(f'{len(display_results)} results · {page_no*PAGE_SIZE+1}–{min((page_no+1)*PAGE_SIZE,len(display_results))}')
            for n,job in enumerate(display_results[page_no*PAGE_SIZE:(page_no+1)*PAGE_SIZE],
                                    start=page_no*PAGE_SIZE):
                with st.container(border=False,key='job_card_'+str(n)):
                    left,right=st.columns([5,1.7],vertical_alignment='top')
                    with left:
                        q=job.get('qualification_match') or {}
                        flagged=[v for v in (q.get('posting_requirement_checks') or [])
                                 if v.get('ranking_caution',0)]
                        relocation=any('Relocation' in (v.get('priority') or '')
                                       for v in (q.get('posting_requirement_checks') or []))
                        check_degree=any(
                            v.get('type')=='Education / professional credential'
                            for v in (q.get('posting_requirement_checks') or []))
                        quality=posting_quality(job)
                        st.markdown(listing_head(
                            job['title'],job['company'],job['location'],
                            job.get('work_style'),job['government'],
                            evidence_index(q) if st.session_state.resume_text.strip() else None,
                            is_new=job.get('new_since_last_search',False),
                            restricted=bool(q.get('application_restricted')),
                            verify=bool(flagged or q.get('career_fit_cautions')),
                            degree=check_degree,relocation=relocation,
                            direct=bool(quality['direct_source'] and quality['individual_url'])
                        ),unsafe_allow_html=True)
                        description_review=assess_description(job)
                        st.caption('**Posting evidence:** '+description_review['label'])
                        if not description_review['detailed']:
                            st.caption('Fit is provisional: missing posting text can hide requirements. Read the original before applying.')
                        if job.get('salary'):
                            st.caption(job['salary'])
                        if job.get('workplace_conflict'):
                            st.caption('Work arrangement: verify')
                        qualification = job.get('qualification_match')
                        if qualification and qualification['resume_present']:
                            st.caption('**Resume alignment:** ' + qualification['label'])
                            transfer=explain_job(job['title'],qualification,True)
                            parts=[]
                            if transfer['family']:
                                ready=job.get('family_readiness')
                                parts.append(transfer['family']+(f' ({ready}% ready)' if ready is not None else ''))
                            if transfer['transfers']:
                                parts.append('you show '+', '.join(a.lower() for a in transfer['transfers']))
                            if transfer['confirmed']:
                                parts.append('confirmed by you: '+', '.join(a.lower() for a in transfer['confirmed']))
                            if transfer['gaps']:
                                parts.append('gaps: '+', '.join(a.lower() for a in transfer['gaps']))
                            if parts:
                                st.caption('**Why it transfers:** '+' · '.join(parts))
                            with st.expander('Match details'):
                                if qualification.get('ranking_overlap_relief',0):
                                    st.caption('Overlapping experience cautions counted once · '
                                               + str(qualification['ranking_overlap_relief'])
                                               + ' duplicate points avoided. Degree and license checks remain separate.')
                                st.write(
                                    f"Resume evidence in {len(qualification['resume_matches'])} "
                                    f"of {qualification['total_areas']} relevant areas mentioned in this listing.")

                                if qualification['resume_matches']:
                                    st.write('**Matches supported by your uploaded resume**')
                                    for item in qualification['resume_matches'][:7]:
                                        st.write('**' + item['area'] + '**')
                                        st.caption('Job posting: ' + item['listing_excerpt'])
                                        for excerpt in item['resume_evidence'][:2]:
                                            st.caption('Your resume: ' + excerpt)
                                if qualification['confirmed_only']:
                                    st.write('**Experience you confirmed separately, not identified in your resume**')
                                    for item in qualification['confirmed_only'][:6]:
                                        st.write('• ' + item['area'])
                                        st.caption('Job posting: ' + item['listing_excerpt'])
                                if qualification['not_documented']:
                                    st.write('**Experience to confirm or document**')
                                    for item in qualification['not_documented'][:7]:
                                        st.write('• ' + item['area'])
                                        st.caption('Job posting: ' + item['listing_excerpt'])
                                    st.caption('Not mentioned in your resume does NOT mean you lack the experience.')
                                if qualification.get('specialized_requirements'):
                                    st.write('**Industry-specific experience to examine**')
                                    for specialization in qualification['specialized_requirements'][:5]:
                                        st.write('• ' + specialization['area'])
                                        st.caption('Job posting: ' + specialization['listing_excerpt'])
                                        st.caption(specialization['resume_status'])
                                if qualification.get('posting_requirement_checks'):
                                    st.write('**Employer-stated minimums and application rules**')
                                    for requirement in qualification['posting_requirement_checks'][:10]:
                                        st.write('**'+requirement['area']+'** — '+requirement['priority'])
                                        st.caption('Employer posting: '+requirement['listing_excerpt'])
                                        st.caption('Résumé review: '+requirement['resume_status'])
                                if qualification['screeners']:
                                    st.write('**Education, credentials, eligibility and years to verify**')
                                    for requirement in qualification['screeners']:
                                        st.write('**' + requirement['type'] + '** — ' + requirement['priority'])
                                        st.caption('Job posting: ' + requirement['listing_excerpt'])
                                        st.caption('Your resume: ' + requirement['resume_status'])
                                if qualification.get('cautions'):
                                    st.write('**Important qualification cautions**')
                                    for warning in qualification['cautions'][:6]:
                                        st.caption('• ' + warning)
                                st.caption(qualification.get('description_completeness',''))
                                if not qualification['total_areas'] and not qualification['screeners']:
                                    st.info('The public feed has limited job requirements. Read the full employer posting before deciding.')
                                st.write('**Resume focus:** ' + qualification['resume_focus'])
                            with st.expander('Tailoring sheet'):
                                sheet=build_sheet(job,st.session_state.resume_text)
                                if sheet['lead_with']:
                                    st.write('**Lead with**')
                                    for item in sheet['lead_with']:
                                        st.write('• '+item['area'])
                                        if item['resume']:
                                            st.caption('Your resume: '+item['resume'])
                                if sheet['add_to_resume']:
                                    st.write('**You confirmed these, but the resume does not say so:** '
                                             +', '.join(sheet['add_to_resume']))
                                if sheet['missing_terms']:
                                    st.write('**Words they repeat that your resume never uses:** '
                                             +', '.join(sheet['missing_terms']))
                                    st.caption('Use them only where they are true for you.')
                                if sheet['gaps']:
                                    st.write('**Gaps to address:** '+', '.join(sheet['gaps']))
                                download_file_widget('Download tailoring sheet',sheet_text(sheet),
                                    'tailoring_'+re.sub(r'[^A-Za-z0-9]+','_',job['title'])[:50]+'.txt',
                                    'text/plain','tailoring_sheet_'+str(n))

                    with right:
                        st.link_button('View job',job['url'],use_container_width=True)
                        if st.button('Save',key=f'clean_save_{n}',use_container_width=True):
                            if save_result_to_tracker(job):
                                st.info('Added to Job Tracker. Storage status is shown above.')
                            else:
                                st.info('Already saved')
                    with st.expander('Employer verification'):
                        render_employer_checker(job,n,_secret('SEC_CONTACT_EMAIL'),on_change=persist_tracker_if_unlocked)
            before, middle, after=st.columns([1,2,1],vertical_alignment='center')
            with before:
                if st.button('← Previous',disabled=page_no==0,use_container_width=True):
                    st.session_state.search_page=page_no-1
                    st.rerun()
            with middle:
                st.caption(f'Page {page_no+1} of {page_total}')
            with after:
                if st.button('Next →',disabled=page_no>=page_total-1,use_container_width=True):
                    st.session_state.search_page=page_no+1
                    st.rerun()
        with st.expander('Source coverage and diagnostics'):
            download_file_widget('Download source coverage report',
                json.dumps({'version':MATCHING_ENGINE_VERSION,'search_run_id':stats.get('run_id'),
                            'sources':stats.get('board_health',[]),'errors':stats.get('errors',[]),
                            'search_status':stats.get('search_status','complete'),
                            'elapsed_seconds':stats.get('elapsed_seconds'),
                            'first_results_seconds':stats.get('first_results_seconds')},
                           ensure_ascii=False,default=str,indent=2).encode('utf-8'),
                'source_coverage_'+stats.get('run_id','unknown')+'.json','application/json','source_coverage_report')
            configured_states = sorted({a[2] for a in GOVERNMENT_AGENCIES} | {a[2] for a in SCHOOLJOBS_AGENCIES})
            returned_states = sorted({code for job in all_results if job['government'] for code in states_in_location(job.get('location', ''))})
            st.caption(f'{len(GOVERNMENT_AGENCIES)} government agency feeds and {len(SCHOOLJOBS_AGENCIES)} education feeds are configured in job_sources.json, plus private employer boards and NYC Open Data. These cover {len(configured_states)} states by employer location (not guaranteed live jobs).')
            st.write(f'**Government states configured:** {", ".join(configured_states) or "None"}')
            st.write(f'**States with matching government results:** {", ".join(returned_states) or "None in this search"}')
            st.caption('Feed status separates agencies returning items, empty feeds, and unavailable feeds. A catalog edit invalidates cached results for affected source types.')
            st.caption('A configured agency does not guarantee that its RSS is available or that a relevant opening exists. You can maintain and disable boards in job_sources.json without changing app.py.')
            st.write('Job providers returned:')
            for name,count in sorted(stats['sources'].items()):
                st.write(f'• {name}: {count}')
            board_rows=stats.get('board_health') or []
            if board_rows:
                healthy=sum(row['status']=='Active' for row in board_rows)
                empty=sum(row['status']=='Empty' for row in board_rows)
                failed=sum(row['status']=='Failed' for row in board_rows)
                partial=sum(row['status']=='Partial' or row.get('truncated',False) for row in board_rows)
                st.write(f'**Career-board health:** {healthy} returned records · '
                         f'{empty} responded with zero qualifying feed records · '
                         f'{failed} were unavailable · {partial} were partial or capped')
                for source_row in board_rows:
                    if source_row.get('recovery_url'):
                        st.link_button('Open official careers: '+source_row['board'],source_row['recovery_url'])
                        st.caption(source_row['recovery_note'])
                filter_health=st.selectbox('Board status',[
                    'All boards','Active','Empty','Partial','Failed'],key='board_health_filter')
                shown=[r for r in board_rows if filter_health=='All boards'
                       or r['status']==filter_health]
                st.dataframe(pd.DataFrame(shown),hide_index=True,use_container_width=True)
                lever_rows=[x for x in board_rows
                            if x.get('provider')=='Lever employer boards']
                if lever_rows:
                    st.markdown('**Lever source audit**')
                    columns=('board','status','provider_records','us_records',
                             'recent_us','non_remote_recent_us',
                             'records','pages','truncated','note','error')
                    st.dataframe(pd.DataFrame([
                        {key:rec.get(key) for key in columns} for rec in lever_rows
                    ]),hide_index=True,use_container_width=True)
                    st.caption('Provider records are published vacancies, '
                               'US and recent counts reflect source filtering; '
                               'final job matches also depend on role and résumé filters.')
                st.caption('Active means the provider returned candidate records, not that an '
                           'eligible role survived the 45-day, location and resume filters. '
                           'Empty means no candidate records survived provider parsing; it '
                           'does not prove an employer has no jobs.')
            st.write(f"Excluded by extra search preferences: {stats['excluded'].get('preferences',0)}")
            if stats.get('preferences'):
                st.caption('Advanced filters: '+str(stats['preferences']))
            st.write(f"Raw records: {stats['fetched']} · Excluded as old: {stats['excluded']['old']} · No publication date: {stats['excluded']['undated']} · Outside location: {stats['excluded']['location']} · Hidden by optional employer limit: {stats['excluded'].get('employer_limit',0)}")
            if stats['errors']:
                st.caption(f"{len(stats['errors'])} feeds had errors or were unavailable; successful feeds still contribute jobs.")
                if st.checkbox('Show unavailable feeds', key='show_unavailable_feeds'):
                    for err in stats['errors']:
                        st.caption('• ' + err)
            st.caption('USAJOBS can also be included automatically if your account already has its free API credentials in Streamlit Secrets. Paid Adzuna and OpenAI APIs are not used. Indeed and LinkedIn do not provide unrestricted public job-search feeds for this app.')
