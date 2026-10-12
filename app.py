import streamlit as st
import re
import fitz  # PyMuPDF
from docx import Document
from io import BytesIO

st.set_page_config(
    page_title="AI Job Finder",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 AI Job Finder")
st.write(
    "Upload your resume to identify your skills "
    "and prepare for personalized job matching."
)

resume = st.file_uploader(
    "Upload your resume",
    type=["pdf", "docx", "txt"]
)

def extract_resume_text(file):
    filename = file.name.lower()
    content = file.getvalue()

    if filename.endswith(".pdf"):
        pdf = fitz.open(stream=content, filetype="pdf")
        return "\n".join(page.get_text() for page in pdf)

    elif filename.endswith(".docx"):
        doc = Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)

    elif filename.endswith(".txt"):
        return content.decode("utf-8", errors="replace")

    return ""

if resume:
    try:
        text = extract_resume_text(resume)

        if not text.strip():
            st.warning(
                "No text was found. If your PDF is scanned, "
                "it may need OCR."
            )
        else:
            st.subheader("Resume Preview")
            st.text_area(
                "Extracted text",
                text,
                height=250
            )

            common_skills = [
                "Python", "SQL", "Excel", "Power BI",
                "Tableau", "Project Management",
                "Data Analysis", "Machine Learning",
                "JavaScript", "Leadership",
                "Communication", "Sales", "Marketing",
                "Customer Service", "AWS", "Azure",
                "Accounting", "Financial Analysis",
                "Writing", "Research", "Operations",
                "Human Resources", "Recruiting",
                "Java", "HTML", "CSS", "Agile"
            ]

            found_skills = [
                skill for skill in common_skills
                if re.search(
                    r"\b" + re.escape(skill) + r"\b",
                    text,
                    re.IGNORECASE
                )
            ]

            st.subheader("Skills Found")

            if found_skills:
                st.write(", ".join(found_skills))
            else:
                st.info(
                    "No skills from the starter list were detected."
                )

            st.success(
                "Resume uploaded and processed successfully!"
            )

    except Exception as error:
        st.error(f"Could not read the resume: {error}")
