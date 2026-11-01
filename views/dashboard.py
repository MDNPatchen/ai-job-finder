"""Dashboard page."""
from app_core import *  # noqa: F401,F403  shared helpers, constants and Streamlit


def render():
    with st.container(border=False, key='dashboard_content'):
        st.markdown(hero('Dashboard','Your applications at a glance'),unsafe_allow_html=True)
        jobs = st.session_state.jobs
        a, b, c = st.columns(3, gap='large')
        a.metric('Tracked Jobs', len(jobs))
        b.metric('Applied', sum(j['Status'] == 'Applied' for j in jobs))
        c.metric('Interviewing', sum(j['Status'] == 'Interviewing' for j in jobs))
        a, b, c = st.columns(3, gap='large')
        a.metric('Offers', sum(j['Status'] == 'Offer' for j in jobs))
        b.metric('Saved', sum(j['Status'] == 'Saved' for j in jobs))
        c.metric('Skipped', sum(j['Status'] == 'Skipped' for j in jobs))
        recent_search=st.session_state.get('search_results')
        if recent_search is not None:
            st.markdown('<div class="job-module-heading">Latest search</div>',
                        unsafe_allow_html=True)
            confirmed=sum((j.get('work_style') in ('On-site','Hybrid','Remote'))
                          for j in recent_search)
            detailed=sum(has_detailed_description(j) for j in recent_search)
            sm1,sm2,sm3=st.columns(3, gap='large')
            sm1.metric('Ranked openings',len(recent_search))
            sm2.metric('Workplace identified',confirmed)
            sm3.metric('More complete descriptions',detailed)

        today=date.today()
        followups=upcoming_followups(jobs,today)
        if followups:
            st.markdown('<div class="job-module-heading">Upcoming follow-ups</div>',unsafe_allow_html=True)
            st.caption(f'{len(followups)} follow-ups due within seven days, including overdue actions.')
            for when,index,item in followups[:8]:
                label='Overdue' if when<today else 'Today' if when==today else when.strftime('%b %d')
                st.write(f"**{label}** · {item['Company']} — {item['Job Title']}")
                if st.button('Mark follow-up complete',key=f'complete_followup_{index}'):
                    complete_followup(jobs,index)
                    persist_tracker_if_unlocked()
                    st.rerun()
        if jobs:
            st.dataframe(pd.DataFrame(jobs), use_container_width=True, hide_index=True)
        else:
            st.caption('No tracked jobs yet.')
