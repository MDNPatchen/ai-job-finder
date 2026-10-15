"""Conservative job-fit cautions beyond shared generic business keywords.

This module does not decide eligibility. It distinguishes transferable duties
from job-specific professional specialization and career-stage mismatch.
All penalties are title-grounded and waived when the uploaded resume contains
specific evidence in that field. Unrelated generic 'manager' matches never
substitute for a regulated or technical field.
"""
import re

# Patterns deliberately match job specialization, not sector names alone.
# A finance *operations* job can remain relevant even at a hospital, but a
# senior accountant requires accounting-specific work.
SPECIALIZED_TITLE_FIELDS = (
    ("Engineering / skilled technical work",
     r"\b(?:engineer(?:ing)?|HVAC|electrician|mechanic|"
     r"building maintenance|maintenance scheduler|facilities technician)\b",
     r"\b(?:engineer(?:ing)?|HVAC|electrician|mechanic|technical maintenance|"
     r"building systems|PE license|professional engineer)\b", 28),
    ("IT / software systems administration",
     r"\b(?:IT manager|information technology|enterprise applications|"
     r"software|cybersecurity|systems administrator|network administrator|"
     r"cloud architect|GTM engineer|technical infrastructure)\b",
     r"\b(?:information technology|IT operations|IT management|"
     r"software development|software engineering|cybersecurity|"
     r"systems administration|enterprise applications)\b", 24),
    ("Specialist accounting / capital markets",
     r"\b(?:accountant|accounting manager|controller|treasury manager|"
     r"capital markets|financial analyst|FP&A|tax manager|auditor|"
     r"chief financial officer)\b",
     r"\b(?:accounting|accountant|controller|treasury|"
     r"capital markets|investment banking|FP&A|financial modeling|"
     r"certified public accountant|chief financial officer|CFO)\b", 23),
    ("Clinical / patient care",
     r"\b(?:ultrasound|nursing|nurse|clinical|physician|"
     r"patient care|medical specialist|radiolog\w*)\b",
     r"\b(?:clinical care|nursing|patient care|healthcare practitioner|"
     r"hospital clinical|licensed physician|ultrasound)\b", 30),
    ("Advanced data journalism / research",
     r"\b(?:data journalist|data scientist|machine learning|"
     r"quantitative research|scientific researcher)\b",
     r"\b(?:data journalism|investigative data reporting|"
     r"scientific research|machine learning|data science)\b", 22),
    ("Law enforcement / court practice",
     r"\b(?:juvenile court officer|probation officer|police officer|"
     r"correctional officer|law enforcement|court clerk)\b",
     r"\b(?:court operations|law enforcement|probation|"
     r"corrections|judicial services|police officer)\b", 24),
    ("Specialist compensation / HR practice",
     r"\b(?:compensation (?:and equity|manager)|total rewards|"
     r"talent strategy|human resources (?:specialist|director)|"
     r"HR generalist)\b",
     r"\b(?:compensation strategy|total rewards|human resources|"
     r"talent acquisition|employee relations|HR management)\b", 14),
    ("Teaching / curriculum specialization",
     r"\b(?:teacher|education program consultant|curriculum (?:director|specialist)|"
     r"principal of (?:a )?school|STEM education)\b",
     r"\b(?:classroom teaching|school curriculum|teaching credential|"
     r"education program consultant|K-12 instruction)\b", 20),
)

# Apply only where the user resume establishes a long senior-management career.
_SENIOR_BACKGROUND = re.compile(
    r"\b(?:publisher|operations director|managing director|"
    r"regional director|general manager|chief operating officer|"
    r"senior manager|executive leadership)\b", re.I)
_CAREER_YEARS = re.compile(
    r"\b(?:1[5-9]|[2-9]\d)\s*\+?\s*years?\b", re.I)
_SENIOR_MANAGEMENT_HISTORY = re.compile(
    r"\b(?:director|publisher|executive|general manager)\b", re.I)


def _long_leadership_history(resume):
    text = str(resume or "")
    return bool(_SENIOR_BACKGROUND.search(text) and
                (_CAREER_YEARS.search(text) or
                 (len(_SENIOR_MANAGEMENT_HISTORY.findall(text)) >= 3)))


def _career_stage_caution(title, resume):
    if not _long_leadership_history(resume):
        return None
    t = str(title or "")
    if re.search(r"\b(?:intern|internship|trainee|apprentice)\b",t,re.I):
        return ("Early-career internship or trainee role",
                "The job title indicates an early-career role despite extensive "
                "leadership experience documented in the résumé.", 35)
    if re.search(r"\b(?:shift lead|team lead|executive assistant|"
                 r"administrative assistant|office assistant|"
                 r"intake coordinator|finance coordinator)\b",t,re.I):
        return ("Career-stage mismatch to review",
                "The posting appears to have a narrower individual-contributor "
                "or first-line scope than the résumé's senior-management history.", 20)
    if re.search(r"\b(?:assistant manager|assistant general manager)\b",t,re.I):
        return ("Assistant-level scope to review",
                "This could be a valid industry transition, but its stated scope "
                "may be below the résumé's demonstrated management responsibilities.", 13)
    if re.search(r"\b(?:entry[- ]level|junior)\b",t,re.I):
        return ("Early-career level to review",
                "This role is explicitly junior or entry-level compared with "
                "the résumé's management history.", 20)
    return None


def evaluate_career_fit(job, resume):
    """Return transparent review cautions and bounded comparative penalties.

    A flag is NOT an assertion that the candidate is unqualified or that an
    employer would not hire them. Resume keywords must be role-specific to
    neutralize a technical-specialization caution.
    """
    title = str(job.get("title") or "")
    resume_text = str(resume or "")
    findings = []
    stage = _career_stage_caution(title,resume_text)
    if stage:
        area, reason, penalty = stage
        findings.append({"area":area, "reason":reason, "ranking_caution":penalty,
                         "needs_verification":True})
    for area, title_pattern, evidence_pattern, penalty in SPECIALIZED_TITLE_FIELDS:
        if re.search(title_pattern,title,re.I) and not re.search(evidence_pattern,resume_text,re.I):
            findings.append({
                "area":area,
                "reason":"The title signals specialized professional duties. "
                         "The uploaded résumé does not clearly document this field; "
                         "verify the full requirements before applying.",
                "ranking_caution":penalty,
                "needs_verification":True,
            })
    # An overlap in related specialist signals must not compound to an
    # absurd penalty (e.g., IT + engineering for a technical systems engineer).
    total = min(42,sum(f["ranking_caution"] for f in findings))
    return {"penalty":total, "cautions":findings}
