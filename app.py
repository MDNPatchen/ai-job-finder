import streamlit as st
import re
import fitz
import pandas as pd
from docx import Document
from io import BytesIO
from datetime import date

# ---------------------------------
# APP SETTINGS
# ---------------------------------

st.set_page_config(
    page_title="AI Job Finder",
    page_icon="💼",
    layout="wide"
)

# ---------------------------------
# SESSION DATA
# ---------------------------------

if "jobs" not in st.session_state:
    st.session_state.jobs = []

if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

if "confirmed_titles" not in st.session_state:
    st.session_state.confirmed_titles = []

# ---------------------------------
# RESUME READER
# ---------------------------------

def extract_resume_text(uploaded_file):
    file_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        text = ""
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            for page in pdf:
                text += page.get_text() + "\n"
        return text

    elif filename.endswith(".docx"):
        document = Document(BytesIO(file_bytes))
        paragraphs = [p.text for p in document.paragraphs]

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    paragraphs.append(cell.text)

        return "\n".join(paragraphs)

    elif filename.endswith(".txt"):
        return file_bytes.decode(
            "utf-8-sig",
            errors="replace"
        )

    return ""


# ---------------------------------
# SKILL RECOGNITION
# ---------------------------------

SKILLS = [
    "Project Management",
    "Program Management",
    "Operations Management",
    "Leadership",
    "Team Management",
    "Strategic Planning",
    "Budget Management",
    "Financial Analysis",
    "Business Development",
    "Customer Service",
    "Sales",
    "Marketing",
    "Communication",
    "Problem Solving",
    "Process Improvement",
    "Training",
    "Recruiting",
    "Human Resources",
    "Microsoft Excel",
    "Microsoft Word",
    "Microsoft Office",
    "Power BI",
    "SQL",
    "Python",
    "Data Analysis",
    "Inventory Management",
    "Supply Chain",
    "Logistics",
    "Scheduling",
    "Quality Assurance",
    "Compliance",
    "Vendor Management",
    "CRM"
]

def detect_skills(text):
    return [
        skill for skill in SKILLS
        if re.search(
            r"\b" + re.escape(skill) + r"\b",
            text,
            re.IGNORECASE
        )
    ]


# ---------------------------------
# JOB TITLE RECOGNITION
# ---------------------------------

JOB_TITLES = [
    "Chief Executive Officer",
    "Chief Operating Officer",
    "Vice President",
    "Director of Operations",
    "Operations Director",
    "Operations Manager",
    "General Manager",
    "Project Manager",
    "Program Manager",
    "Product Manager",
    "Regional Manager",
    "District Manager",
    "Office Manager",
    "Business Analyst",
    "Data Analyst",
    "Sales Manager",
    "Account Manager",
    "Customer Service Manager",
    "Human Resources Manager",
    "Administrative Assistant",
    "Executive Assistant",
    "Supervisor",
    "Team Lead",
    "Coordinator",
    "Consultant",
    "Engineer",
    "Technician",
    "Specialist"
]

def detect_job_titles(text):
    return [
        title for title in JOB_TITLES
        if re.search(
            r"\b" + re.escape(title) + r"\b",
            text,
            re.IGNORECASE
        )
    ]


# ---------------------------------
# NAVIGATION
# ---------------------------------

st.sidebar.title("💼 AI Job Finder")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "My Resume",
        "Find Jobs",
        "Job Tracker"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "Build your resume, find opportunities, "
    "and track your job search."
)

# ---------------------------------
# DASHBOARD
# ---------------------------------

if page == "Dashboard":

    st.title("📊 Job Search Dashboard")

    jobs = st.session_state.jobs

    total = len(jobs)

    applied = sum(
        job["Status"] == "Applied"
        for job in jobs
    )

    interviews = sum(
        job["Status"] == "Interviewing"
        for job in jobs
    )

    offers = sum(
        job["Status"] == "Offer"
        for job in jobs
    )

    saved = sum(
        job["Status"] == "Saved"
        for job in jobs
    )

    skipped = sum(
        job["Status"] == "Skipped"
        for job in jobs
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Jobs", total)
    col2.metric("Applied", applied)
    col3.metric("Interviews", interviews)

    col4, col5, col6 = st.columns(3)

    col4.metric("Offers", offers)
    col5.metric("Saved", saved)
    col6.metric("Skipped", skipped)

    st.divider()

    st.subheader("Recent Job Activity")

    if jobs:
        st.dataframe(
            pd.DataFrame(jobs),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(
            "No jobs tracked yet. "
            "Go to Job Tracker to add your first job."
        )

    st.caption(
        "Counts reflect each job's current status."
    )


# ---------------------------------
# MY RESUME
# ---------------------------------

elif page == "My Resume":

    st.title("📄 My Resume")

    st.write(
        "Upload your resume to identify your skills "
        "and previous job titles."
    )

    uploaded_file = st.file_uploader(
        "Upload your resume",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_file is not None:

        try:
            text = extract_resume_text(
                uploaded_file
            )

            if not text.strip():
                st.warning(
                    "No readable text found in this file."
                )
                st.stop()

            st.session_state.resume_text = text

            st.success(
                "Resume uploaded successfully!"
            )

        except Exception as error:
            st.error(
                f"Unable to read resume: {error}"
            )

    text = st.session_state.resume_text

    if text:

        with st.expander("View Your Resume Text"):
            st.text_area(
                "Extracted resume text",
                value=text,
                height=300
            )

        st.subheader("🛠️ Skills Found")

        skills = detect_skills(text)

        if skills:
            st.write(", ".join(skills))
        else:
            st.info("No listed skills detected.")

        st.subheader("💼 Job Titles Found")

        detected_titles = detect_job_titles(text)

        confirmed_titles = st.multiselect(
            "Confirm your previous job titles",
            options=detected_titles,
            default=detected_titles
        )

        additional_titles = st.text_input(
            "Add missing titles, separated by commas"
        )

        if additional_titles.strip():
            for title in additional_titles.split(","):
                title = title.strip()

                if title and title not in confirmed_titles:
                    confirmed_titles.append(title)

        st.session_state.confirmed_titles = confirmed_titles

        st.markdown("### Confirmed Job Titles")

        if confirmed_titles:
            for title in confirmed_titles:
                st.write("✓", title)
        else:
            st.info("No titles confirmed yet.")

        st.info(
            "Coming next: Resume improvement "
            "suggestions you can approve."
        )


# ---------------------------------
# FIND JOBS
# ---------------------------------

elif page == "Find Jobs":

    st.title("🔎 Find Jobs")

    st.write(
        "This section will search real job listings "
        "and compare them with your resume."
    )

    keyword = st.text_input(
        "Job title or keywords",
        placeholder="Operations Director"
    )

    location = st.text_input(
        "Location",
        placeholder="Rochester, MN or Remote"
    )

    if st.button("Search Jobs"):
        st.info(
            "Live job search is not connected yet. "
            "We'll add this feature next."
        )


# ---------------------------------
# JOB TRACKER
# ---------------------------------

elif page == "Job Tracker":

    st.title("📋 Job Application Tracker")

    st.write(
        "Keep track of jobs you've saved, applied to, "
        "skipped, interviewed for, and more."
    )

    statuses = [
        "Saved",
        "Applied",
        "Interviewing",
        "Offer",
        "Rejected",
        "Skipped",
        "Withdrawn"
    ]

    with st.expander(
        "➕ Add a New Job",
        expanded=True
    ):

        with st.form("add_job_form"):

            company = st.text_input(
                "Company Name"
            )

            title = st.text_input(
                "Job Title"
            )

            location = st.text_input(
                "Location"
            )

            job_url = st.text_input(
                "Job Posting URL"
            )

            salary = st.text_input(
                "Salary or Salary Range"
            )

            status = st.selectbox(
                "Application Status",
                statuses
            )

            applied_date = st.date_input(
                "Date Recorded",
                value=date.today()
            )

            interview_date = st.date_input(
                "Interview Date (if applicable)",
                value=None
            )

            notes = st.text_area(
                "Notes / Follow-up Details"
            )

            submitted = st.form_submit_button(
                "Save Job"
            )

            if submitted:

                if not company.strip() or not title.strip():
                    st.warning(
                        "Please enter a company and job title."
                    )

                else:

                    new_job = {
                        "Company": company.strip(),
                        "Job Title": title.strip(),
                        "Location": location.strip(),
                        "Job URL": job_url.strip(),
                        "Salary": salary.strip(),
                        "Status": status,
                        "Date Recorded": str(applied_date),
                        "Interview Date": (
                            str(interview_date)
                            if interview_date
                            else ""
                        ),
                        "Notes": notes.strip()
                    }

                    st.session_state.jobs.append(
                        new_job
                    )

                    st.success(
                        "Job added successfully!"
                    )

    st.divider()

    st.subheader("Your Tracked Jobs")

    jobs = st.session_state.jobs

    if jobs:

        status_filter = st.selectbox(
            "Filter by status",
            ["All"] + statuses
        )

        filtered_jobs = [
            job for job in jobs
            if status_filter == "All"
            or job["Status"] == status_filter
        ]

        st.dataframe(
            pd.DataFrame(filtered_jobs),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Update a Job")

        job_options = [
            f"{i + 1}. {job['Company']} - {job['Job Title']}"
            for i, job in enumerate(jobs)
        ]

        selected_job = st.selectbox(
            "Choose a job to update",
            range(len(job_options)),
            format_func=lambda i: job_options[i]
        )

        current_job = jobs[selected_job]

        new_status = st.selectbox(
            "New Status",
            statuses,
            index=statuses.index(
                current_job["Status"]
            )
        )

        new_notes = st.text_area(
            "Update Notes",
            value=current_job["Notes"],
            key=f"notes_{selected_job}"
        )

        if st.button("Save Changes"):

            st.session_state.jobs[
                selected_job
            ]["Status"] = new_status

            st.session_state.jobs[
                selected_job
            ]["Notes"] = new_notes

            st.success(
                "Job updated successfully!"
            )

            st.rerun()

        st.divider()

        csv_data = pd.DataFrame(
            st.session_state.jobs
        ).to_csv(index=False)

        st.download_button(
            "⬇️ Download Job Tracker (CSV)",
            data=csv_data,
            file_name="job_tracker.csv",
            mime="text/csv"
        )

    else:
        st.info(
            "No jobs added yet. "
            "Use the form above to track your first job."
        )
