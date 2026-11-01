"""My Resume page."""
from app_core import *  # noqa: F401,F403  shared helpers, constants and Streamlit


def render():
    st.markdown(hero('Resume','Upload and review your experience'),unsafe_allow_html=True)
    file = st.file_uploader('Upload PDF, Word, or TXT resume', type=['pdf','docx','txt'])
    keep = st.checkbox('Save my resume with my Job Tracker so the analysis is ready next time',
        value=st.session_state.save_resume_with_tracker,
        help='Off by default. When on, the resume text is stored in your private cloud tracker '
             '(when unlocked) and in tracker backup files. It is never stored in GitHub.')
    if keep != st.session_state.save_resume_with_tracker:
        st.session_state.save_resume_with_tracker = keep
        persist_tracker_if_unlocked()  # adds or removes the saved copy
    if file:
        try:
            extracted = extract_resume_text(file)
            if extracted.strip():
                if extracted != st.session_state.resume_text:
                    st.session_state.resume_text = extracted
                    # Old search results were ranked with an earlier resume.
                    st.session_state.pop('search_results', None)
                    st.session_state.pop('search_stats', None)
                    persist_tracker_if_unlocked()
                st.success('Resume uploaded successfully!')
            else:
                st.warning('No readable text was found. Scanned PDFs may need OCR.')
        except Exception as exc:
            st.error(f'Unable to read file: {exc}')
    text = st.session_state.resume_text
    if text:
        # Analysis runs automatically from the resume and profile; searches
        # use it for matching and to explain each listing.
        render_resume_interpretation(text)
        verification_editor()
        with st.expander('View extracted resume text'):
            st.text_area('Resume text', text, height=280)
        st.info('Your resume is analyzed automatically. Search on Find Jobs: every listing shows '
                'its field, what transfers from your experience, and the gaps.')
    else:
        st.info('Upload a resume to begin.')
