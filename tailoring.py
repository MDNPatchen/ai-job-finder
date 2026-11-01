"""Per-job tailoring sheet built from the match the app already ran. No AI.

For one listing: which of your skills to lead with (and the resume line that
proves each), which you confirmed but the resume doesn't show, the words the
posting repeats that your resume never uses, and the requirements to check.
"""
import re
from collections import Counter

from role_families import family_for_title

_STOP = set("""
a about above after again all also am an and any are as at be because been before being below between both but by
can could did do does doing down during each few for from further had has have having he her here hers him his how
i if in into is it its itself just me more most my no nor not now of off on once only or other our ours out over own
same she should so some such than that the their theirs them then there these they this those through to too under
until up very was we were what when where which while who whom why will with would you your yours
able ability across activities additional all applicants applicant apply benefits candidate candidates company
including include includes job jobs position positions preferred required requirements requires responsibilities
responsible role skills strong team teams work working years year experience must well within various
equal opportunity employer employment status disability veteran race color religion sex sexual orientation gender
identity national origin age protected law laws accommodation accommodations individuals qualified
time full part day days hours week salary pay range per hour annual compensation dental vision insurance
""".split())
_WORD = re.compile(r"[A-Za-z][A-Za-z&'\-]{2,}")


def _tokens(text):
    return [w.lower().strip("'-") for w in _WORD.findall(text or '')]


def missing_terms(description, resume, employer='', limit=10):
    """Words and two-word phrases the posting repeats that the resume never uses."""
    resume_text = ' '.join(_tokens(resume))
    if employer.strip():  # the employer's own name is not a skill to add
        description = re.sub(re.escape(employer.strip()), ' ', description or '', flags=re.I)
    skip = set()
    counts, pairs = Counter(), Counter()
    # Phrases never span punctuation: "...communications. Partner" is not a phrase.
    for clause in re.split(r'[.;:,!?()\n•|/]+', description or ''):
        words = [w for w in _tokens(clause) if w not in _STOP and len(w) > 3 and w not in skip]
        counts.update(words)
        pairs.update(f'{a} {b}' for a, b in zip(words, words[1:]) if a != b)
    found = []
    for phrase, n in pairs.most_common(40):
        if n >= 2 and phrase not in resume_text and not any(phrase in f for f, _ in found):
            found.append((phrase, n))
    for word, n in counts.most_common(80):
        stem = word[:6]
        if n >= 2 and stem not in resume_text and not any(word in f for f, _ in found):
            found.append((word, n))
    found.sort(key=lambda x: (-x[1], x[0]))
    return [phrase for phrase, _ in found[:limit]]


def build_sheet(job, resume_text):
    q = job.get('qualification_match') or {}
    family = family_for_title(job.get('title'))
    weight = family['skills'] if family else {}
    lead = [m for m in q.get('resume_matches') or [] if m.get('match_origin') != 'Job title only']
    lead.sort(key=lambda m: -weight.get(m['area'], 0))
    requirements = []
    for item in (q.get('posting_requirement_checks') or []) + (q.get('screeners') or []):
        label = item.get('area') or item.get('type') or 'Requirement'
        status = item.get('resume_status') or ''
        key = (label, item.get('listing_excerpt', '')[:60])
        if key not in {(r['label'], r['excerpt'][:60]) for r in requirements}:
            excerpt = re.sub(r'\s+', ' ', item.get('listing_excerpt', '')).strip()
            requirements.append({'label': label, 'excerpt': excerpt[:160] + ('…' if len(excerpt) > 160 else ''),
                                 'status': status})
    return {
        'title': job.get('title', ''), 'company': job.get('company', ''), 'url': job.get('url', ''),
        'family': family['label'] if family else '',
        'lead_with': [{'area': m['area'], 'resume': (m.get('resume_evidence') or [''])[0],
                       'posting': m.get('listing_excerpt', '')} for m in lead[:4]],
        'add_to_resume': [m['area'] for m in q.get('confirmed_only') or []][:4],
        'gaps': [m['area'] for m in q.get('not_documented') or []][:4],
        'missing_terms': missing_terms(job.get('description', ''), resume_text, job.get('company', '')),
        'requirements': requirements[:6],
    }


def sheet_text(sheet):
    """Plain-text version for download."""
    out = [f"TAILORING SHEET — {sheet['title']} at {sheet['company']}"]
    if sheet['family']:
        out.append(f"Field: {sheet['family']}")
    out.append(f"Posting: {sheet['url']}\n")
    out.append('LEAD WITH (your strongest overlap, in this order)')
    for item in sheet['lead_with'] or [{'area': 'No direct overlap found in the posting text', 'resume': '', 'posting': ''}]:
        out.append(f"- {item['area']}")
        if item['resume']:
            out.append(f"    Your resume: {item['resume']}")
        if item['posting']:
            out.append(f"    They ask: {item['posting']}")
    if sheet['add_to_resume']:
        out.append('\nYOU CONFIRMED THESE, BUT THE RESUME DOES NOT SAY SO — add a bullet')
        out += [f'- {a}' for a in sheet['add_to_resume']]
    if sheet['missing_terms']:
        out.append('\nWORDS THEY REPEAT THAT YOUR RESUME NEVER USES (use them only where true)')
        out.append('- ' + ', '.join(sheet['missing_terms']))
    if sheet['gaps']:
        out.append('\nGAPS TO ADDRESS IN A COVER LETTER OR INTERVIEW')
        out += [f'- {a}' for a in sheet['gaps']]
    if sheet['requirements']:
        out.append('\nREQUIREMENTS TO CHECK BEFORE APPLYING')
        for r in sheet['requirements']:
            out.append(f"- {r['label']}: {r['excerpt']}")
            if r['status']:
                out.append(f"    {r['status']}")
    return '\n'.join(out) + '\n'
