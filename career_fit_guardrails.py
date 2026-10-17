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
    ("Payroll systems / compliance specialization",
     r"\bpayroll\b",
     r"\b(?:payroll (?:administration|processing|management|systems|compliance)|payroll tax|time capture systems)\b", 22),
    ("Healthcare revenue cycle specialization",
     r"\b(?:revenue cycle|patient billing|patient financial services)\b",
     r"\b(?:revenue cycle|patient billing|patient financial services|medical billing|healthcare reimbursement)\b", 24),
    ("Merchant payments specialization",
     r"\b(?:payments? (?:performance|operations|product|strategy)|merchant (?:payments?|acquiring))\b",
     r"\b(?:payments? (?:operations|processing|acceptance|experience)|merchant (?:acquiring|payments?)|card network|payment gateway)\b", 22),
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
    ("Dedicated corporate finance / investment analysis",
     r"\b(?:corporate finance|financial planning\s*(?:and|&)\s*analysis|"
     r"FP&A|investment banking|treasury analytics?)\b",
     r"\b(?:corporate finance|financial modeling|"
     r"financial planning\s*(?:and|&)\s*analysis|"
     r"FP&A|investment banking|investment analysis|"
     r"treasury operations|treasury analytics?)\b",22),
    ("Construction project / preconstruction leadership",
     r"\b(?:preconstruction|construction project manager|"
     r"capital project manager|construction operations director|"
     r"construction estimating manager)\b",
     r"\b(?:preconstruction|construction management|"
     r"construction project management|construction estimating|"
     r"commercial construction|capital construction projects?)\b",24),
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
    ("Industrial environmental health & safety specialization",
     r"\b(?:EHS|HSE)\s+(?:specialist|manager|director|coordinator)\b|"
     r"\b(?:environmental (?:health\s*(?:and|&)\s*)?safety)\s+"
     r"(?:specialist|manager|director)\b",
     r"\b(?:environmental health (?:and|&) safety|EHS management|"
     r"OSHA compliance|industrial safety management)\b", 25),
    ("Professional UX / product design",
     r"\b(?:product design|UX design|UI design|user.experience design|"
     r"product designer|UX designer)\b",
     r"\b(?:product design|UX design|UI design|user.experience design|"
     r"Figma|professional design portfolio)\b", 25),
    ("Equity compensation and total rewards specialty",
     r"\b(?:compensation\s*(?:&|and)\s*equity|equity compensation|"
     r"compensation manager|total rewards manager)\b",
     r"\b(?:equity compensation|stock (?:option|award) administration|"
     r"compensation administration|total rewards strategy|"
     r"salary benchmarking|pay equity analysis)\b", 24),
    ("Laboratory science / mass spectrometry",
     r"\b(?:senior scientist|sr\.?\s*scientist|mass spec|"
     r"LC[- ]?MS/?MS|bioanalytical scientist|research scientist)\b",
     r"\b(?:laboratory research|mass spectrometry|LC[- ]?MS/?MS|"
     r"bioanalytical testing|analytical chemistry)\b", 32),
    ("IT technical project delivery",
     r"\b(?:I\.?T\.? project manager|information technology project manager|"
     r"technical project manager|systems implementation project manager)\b",
     r"\b(?:IT project management|technology project management|"
     r"enterprise IT implementation|software systems integration)\b", 23),
    ("Dedicated social media strategy / campaigns",
     r"\b(?:senior\s+)?social media (?:manager|director|lead|specialist)\b|"
     r"\b(?:paid social|social media strategist)\b",
     r"\b(?:social media (?:strategy|management|marketing|campaigns?|"
     r"content strategy)|paid social (?:campaigns?|advertising)|"
     r"social media channel management)\b", 21),
    ("Music rights and licensing clearances",
     r"\b(?:music rights?|music licens(?:e|ing)|"
     r"music clearances?|music copyright|sync licensing)\b",
     r"\b(?:music rights? administration|music licensing|"
     r"music clearances?|music copyright administration|"
     r"synchronization licensing|sync licensing)\b", 24),
    ("Experiential event marketing specialization",
     r"\b(?:experiential marketing|event marketing)\b",
     r"\b(?:event marketing|experiential marketing|"
     r"event production|large.scale event strategy)\b", 13),
    ("Marketing science / statistical analysis",
     r"\b(?:marketing science|marketing analytics scientist|"
     r"measurement science director)\b",
     r"\b(?:marketing science|marketing mix modeling|"
     r"econometric modeling|statistical programming)\b", 22),
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
    if re.search(r"\b(?:logistics coordinator|administrative specialist\s*\d*|"
                 r"office coordinator|inventory coordinator)\b",t,re.I):
        return ("Coordination / administrative career stage to review",
                "This role appears to emphasize coordination or specialist "
                "duties rather than the broad leadership responsibility "
                "documented in the résumé. Confirm scope and seniority.", 17)
    if re.search(r"\b(?:shift lead|team lead|executive assistant|"
                 r"administrative assistant|office assistant|"
                 r"intake coordinator|finance coordinator)\b",t,re.I):
        return ("Career-stage mismatch to review",
                "The posting appears to have a narrower individual-contributor "
                "or first-line scope than the résumé's senior-management history.", 20)
    if re.search(r"\b(?:assistant store manager|store assistant manager)\b",t,re.I):
        return ("Store assistant-management level to review",
                "A store-level assistant management role may have less scope than "
                "the résumé's multi-location department leadership experience.", 17)
    if re.search(r"\b(?:sourcing specialist|procurement specialist|"
                 r"purchasing specialist|talent acquisition coordinator|"
                 r"recruiting coordinator|recruitment coordinator|"
                 r"marketing coordinator|sales coordinator|"
                 r"purchasing coordinator)\b",t,re.I):
        return ("Specialist or coordinator career level to review",
                "The title suggests an individual-contributor or coordination "
                "position rather than broad department or multi-site leadership. "
                "Verify the actual scope before prioritizing it.", 18)
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
