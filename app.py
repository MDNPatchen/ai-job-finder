import streamlit as st
import re
import fitz
from docx import Document
from io import BytesIO

st.set_page_config(
    page_title="AI Job Finder",
    page_icon="💼",
    layout="wide"
)

st.title("💼 AI Job Finder")
st.write(
    "Upload your resume to identify your skills and job titles. "
    "We'll use this information to help improve your resume "
    "and find matching jobs."
)

# --- Resume Text Extraction ---

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

        # Include text from tables
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    paragraphs.append(cell.text)

        return "\n".join(paragraphs)

    elif filename.endswith(".txt"):
        return file_bytes.decode("utf-8-sig", errors="replace")

    return ""


# --- Skills Recognition ---

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
    found = []

    for skill in SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"

        if re.search(pattern, text, re.IGNORECASE):
            found.append(skill)

    return found


# --- Job Title Recognition ---

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
    found = []

    for title in JOB_TITLES:
        pattern = r"\b" + re.escape(title) + r"\b"

        if re.search(pattern, text, re.IGNORECASE):
            found.append(title)

    return found


# --- Upload Resume ---

uploaded_file = st.file_uploader(
    "Upload your resume",
    type=["pdf", "docx", "txt"]
)

if uploaded_file is not None:

    try:
        text = extract_resume_text(uploaded_file)

        if not text.strip():
            st.warning(
                "No readable text was found. "
                "If your PDF is scanned, it may need OCR."
            )
            st.stop()

        st.success("Resume uploaded successfully!")

        # --- Display Resume ---

        with st.expander("📄 View Your Resume Text"):
            st.text_area(
                "Extracted resume text",
                value=text,
                height=350
            )

        # --- Display Skills ---

        st.subheader("🛠️ Skills Found in Your Resume")

        detected_skills = detect_skills(text)

        if detected_skills:
            st.write(", ".join(detected_skills))
        else:
            st.info(
                "No skills from our current list were detected."
            )

        # --- Display Job Titles ---

        st.subheader("💼 Job Titles Found in Your Resume")

        detected_titles = detect_job_titles(text)

        if detected_titles:
            st.write(
                "Review these possible job titles. "
                "Uncheck any that you have not held."
            )
        else:
            st.info(
                "No common job titles were detected automatically."
            )

        confirmed_titles = st.multiselect(
            "Select your actual previous job titles:",
            options=detected_titles,
            default=detected_titles
        )

        additional_titles = st.text_input(
            "Add missing job titles (separate with commas):"
        )

        if additional_titles.strip():
            for title in additional_titles.split(","):
                title = title.strip()

                if title and title not in confirmed_titles:
                    confirmed_titles.append(title)

        st.markdown("### Your Confirmed Job Titles")

        if confirmed_titles:
            for title in confirmed_titles:
                st.write("✓", title)
        else:
            st.write("No job titles confirmed yet.")

        st.info(
            "Next feature: Resume improvement suggestions "
            "that you can review and approve."
        )

    except Exception as error:
        st.error(f"Unable to read the resume: {error}")

else:
    st.info("Upload your resume to get started.")
