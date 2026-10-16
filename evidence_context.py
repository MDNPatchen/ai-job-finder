"""Conservative affirmative-experience checks for literal evidence matching.

These rules avoid known false positives. They are not a semantic credential
verifier; unfamiliar wording still requires review.
"""
import re

_NEGATIVE=re.compile(r"\b(?:no|without|lack(?:ing)?|never|not|haven['’]t|have not|don['’]t|do not)\b",re.I)
_NONEXPERIENCE=re.compile(r'\b(?:seeking|aspir(?:ing|e)|interested in|hope to|want to|wish to|learning about|'
                        r'coursework|course in|course on|studying|job requirements|ideal candidate|job description)\b',re.I)


def clauses(text):
    return re.split(r'(?<=[.!?;])\s+|\n|\bbut\b|\bhowever\b',str(text or ''),flags=re.I)


def is_affirmative(text, start=0, end=None):
    text=str(text or '')
    # "Not only managed budgets, but also ..." is an affirmative construction.
    text=re.sub(r'\bnot\s+only\b','',text,flags=re.I)
    text=re.sub(r'\b(?:without supervision|no service disruptions?|no downtime|no budget overruns?)\b','',text,flags=re.I)
    return not (_NEGATIVE.search(text) or _NONEXPERIENCE.search(text))


def affirmative_match(patterns,text):
    for clause in clauses(text):
        if not is_affirmative(clause):
            continue
        for pattern in patterns:
            match=pattern.search(clause)
            if match:
                return clause,match
    return None


def affirmative_resume_text(text):
    """Prevent negative/aspirational clauses supporting downstream minimums."""
    return '\n'.join(c for c in clauses(text) if is_affirmative(c))
