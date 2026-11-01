"""Interpret a resume and a short self-reported profile, without AI.

Resumes both understate and overstate. This module grades every skill claim
by WHERE it appears and HOW it is supported, and lets the person confirm or
overrule the resume with short answers:

  Proven      - a work-experience bullet with a number, $ or % attached
  Described   - a work-experience bullet without numbers
  Volunteer   - only in board / volunteer / community-service entries
  Summary     - only in the summary or skills list (self-description)
  Confirmed   - not in the resume, but the person says they do it
  Not shown   - neither

Profile answers feed matching: "Yes" confirms an area (partial credit, with a
prompt to add it to the resume); "No" removes an area the resume overstates.
"""
import re

from qualification_matcher import CAPABILITIES, is_heading_line, _one_line

_AREA_PATTERNS = tuple((area, tuple(re.compile(p, re.I) for p in patterns))
                       for area, patterns in CAPABILITIES)

# ---- Sections ---------------------------------------------------------------
_SECTION_KINDS = (
    ('summary', re.compile(r'^(?:professional |executive |career )?(?:summary|profile|objective)\b', re.I)),
    ('skills', re.compile(r'^(?:core |key )?(?:competencies|skills|expertise|areas of expertise|strengths)\b', re.I)),
    ('volunteer', re.compile(r'(?:volunteer|community|civic|board|philanthrop|leadership & |service|affiliations)', re.I)),
    ('education', re.compile(r'^(?:education|certifications?|licen[cs]es?|training)\b', re.I)),
    ('experience', re.compile(r'(?:experience|employment|career history|work history)', re.I)),
)


def _section_of(line, current):
    text = _one_line(line, 120)
    # Section headings are short; accept ALL CAPS or Title Case headings.
    if len(text.split()) <= 6 and (text.isupper() or text.istitle() or text.endswith(':')):
        for kind, pattern in _SECTION_KINDS:
            if pattern.search(text):
                return kind, True
    return current, False


_NUMBER = re.compile(r'(?:\$\s?\d|\d+(?:\.\d+)?\s?%|\b\d{2,}(?:,\d{3})*\b|\b\d+(?:\.\d+)?\s?(?:million|billion|thousand|k|m)\b'
                     r'|\b(?:two|three|four|five|six|seven|eight|nine|ten|twelve|dozen)\b'
                     # small counts that state scale: "3 counties", "5 newspapers"
                     r'|\b\d+\s+(?:newspapers|publications|papers|titles|sites|locations|counties|states|regions|markets|'
                     r'departments|teams|people|employees|staff|reps|managers|stores|offices|branches|properties|brands|events)\b)', re.I)
# A bare 4-digit year or a duration is not an outcome.
_YEARS_ONLY = re.compile(r'^\D*(?:19|20)\d{2}\D*$')

# Self-description that recruiters discount and keyword matchers cannot use.
VAGUE_PHRASES = (
    'visionary', 'results-driven', 'results driven', 'dynamic', 'passionate',
    'world-class', 'best-in-class', 'monumental', 'massive', 'sophisticated',
    'innovative', 'high-impact', 'high impact', 'synergy', 'thought leadership',
    'absolute accountability', 'proven track record', 'unique catalyst',
    'go-getter', 'self-starter', 'detail-oriented', 'strategic thinker',
)


def split_resume(text):
    """Return [(section, line)] with heading/date lines removed."""
    out, section = [], 'summary'
    for raw in str(text or '')[:55000].splitlines():
        if not raw.strip():
            continue
        section, is_heading = _section_of(raw, section)
        if is_heading or is_heading_line(raw):
            continue
        out.append((section, _one_line(raw, 500)))
    return _merge_wrapped(out)


def _merge_wrapped(lines):
    """PDF text wraps bullets across lines; rejoin continuations."""
    merged = []
    for section, line in lines:
        starts_new = bool(re.match(r'^[•\-\*▪●◦]|^\d+[.)]\s', line)) or not merged
        if (not starts_new and merged and merged[-1][0] == section
                and not re.search(r'[.!?:]$', merged[-1][1])):
            merged[-1] = (section, merged[-1][1] + ' ' + line)
        else:
            merged.append((section, line))
    return [(s, re.sub(r'^[•\-\*▪●◦]\s*', '', l)) for s, l in merged]


def _has_numbers(line):
    found = [m.group(0) for m in _NUMBER.finditer(line)]
    return any(not _YEARS_ONLY.match(x) for x in found)


# ---- Profile questions --------------------------------------------------------
# kind: 'yn' -> Yes / Partly / No / Not sure ; 'number' -> integer (0 = skip)
PROFILE_QUESTIONS = (
    {'key': 'pnl', 'kind': 'yn', 'question': 'Do you own a full P&L (revenue and expenses), not just an expense budget?',
     'confirms': ('Financial & P&L leadership',), 'excludes': ()},
    {'key': 'budgets', 'kind': 'yn', 'question': 'Do you build annual budgets and forecasts?',
     'confirms': ('Financial & P&L leadership',), 'excludes': ()},
    {'key': 'revenue', 'kind': 'yn', 'question': 'Are you responsible for growing revenue (advertising, subscriptions, printing, events)?',
     'confirms': ('Revenue growth & transformation',), 'excludes': ('Revenue growth & transformation',)},
    {'key': 'ad_sales', 'kind': 'yn', 'question': 'Do you lead an advertising or sales team?',
     'confirms': ('Advertising & sales leadership',), 'excludes': ('Advertising & sales leadership',)},
    {'key': 'managers', 'kind': 'yn', 'question': 'Do you hire, supervise and develop managers or department heads?',
     'confirms': ('Talent & organizational change',), 'excludes': ()},
    {'key': 'editorial', 'kind': 'yn', 'question': 'Do newsroom or editorial leaders report to you?',
     'confirms': ('Editorial & cross-functional leadership',), 'excludes': ('Editorial & cross-functional leadership',)},
    {'key': 'digital', 'kind': 'yn', 'question': 'Do you run digital products or digital revenue (websites, e-editions, digital subscriptions)?',
     'confirms': ('Digital transformation',), 'excludes': ()},
    {'key': 'printing', 'kind': 'yn', 'question': 'Do you oversee printing or production operations (press room, commercial printing)?',
     'confirms': ('Operations leadership',), 'excludes': ()},
    {'key': 'distribution', 'kind': 'yn', 'question': 'Do you run circulation, distribution or delivery operations?',
     'confirms': ('Distribution & logistics',), 'excludes': ()},
    {'key': 'contracts', 'kind': 'yn', 'question': 'Do you negotiate major contracts or vendor agreements?',
     'confirms': ('Negotiation & vendor management',), 'excludes': ()},
    {'key': 'spokesperson', 'kind': 'yn', 'question': 'Are you the spokesperson and handle media or crisis communications?',
     'confirms': ('Communications & public relations',), 'excludes': ('Communications & public relations',)},
    {'key': 'fundraising', 'kind': 'yn', 'question': 'Have you personally raised money (donors, sponsorships, grants)?',
     'confirms': ('Fundraising & development',), 'excludes': ('Fundraising & development',)},
    {'key': 'board', 'kind': 'yn', 'question': 'Do you report to or work closely with a board of directors?',
     'confirms': ('Strategic planning & execution', 'Community partnerships'), 'excludes': ()},
    {'key': 'government', 'kind': 'yn', 'question': 'Have you worked for a government agency or in public administration?',
     'confirms': ('Government administration',), 'excludes': ('Government administration',)},
    {'key': 'sites', 'kind': 'number', 'question': 'How many publications, sites or locations do you oversee?',
     'confirms_at': 2, 'confirms': ('Multi-site business leadership',)},
    {'key': 'budget_usd', 'kind': 'number', 'question': 'Largest annual budget or revenue you are responsible for ($)',
     'confirms_at': 1, 'confirms': ('Financial & P&L leadership',)},
    {'key': 'headcount', 'kind': 'number', 'question': 'People in the organization you lead (direct and indirect)',
     'confirms_at': 10, 'confirms': ('Talent & organizational change',)},
    {'key': 'years_leading', 'kind': 'number', 'question': 'Years in senior leadership roles',
     'confirms_at': 0, 'confirms': ()},
)
YN_CHOICES = ('Not sure', 'Yes', 'Partly', 'No')

# The eight responsibilities the user confirmed before this profile existed.
# Pre-filled so nothing silently changes; every answer can be edited.
LEGACY_DEFAULT_ANSWERS = {
    'pnl': 'Yes', 'budgets': 'Yes', 'revenue': 'Yes', 'managers': 'Yes',
    'digital': 'Yes', 'distribution': 'Yes', 'contracts': 'Yes', 'sites': 2,
}


def profile_areas(answers):
    """(confirmed, excluded) capability areas from profile answers."""
    confirmed, excluded = set(), set()
    for q in PROFILE_QUESTIONS:
        value = (answers or {}).get(q['key'])
        if q['kind'] == 'yn':
            if value in ('Yes', 'Partly'):
                confirmed.update(q['confirms'])
            elif value == 'No':
                excluded.update(q['excludes'])
        else:
            try:
                number = float(value or 0)
            except (TypeError, ValueError):
                number = 0
            if q['confirms'] and number >= max(1, q.get('confirms_at', 1)):
                confirmed.update(q['confirms'])
    return confirmed - excluded, excluded


# ---- Interpretation -----------------------------------------------------------------
_GRADE_ORDER = ('Proven', 'Described', 'Volunteer', 'Summary', 'Confirmed', 'Not shown', 'Overruled')
# What a senior publisher / general-manager resume is normally expected to show.
EXPECTED_FOR_LEADERS = (
    'Financial & P&L leadership', 'Revenue growth & transformation',
    'Talent & organizational change', 'Multi-site business leadership',
    'Advertising & sales leadership', 'Digital transformation',
)


def interpret_resume(text, answers=None):
    """Grade every capability area; list vague phrases and missing numbers."""
    lines = split_resume(text)
    confirmed, excluded = profile_areas(answers)
    rows = []
    for area, patterns in _AREA_PATTERNS:
        hits = [(section, line) for section, line in lines
                if any(p.search(line) for p in patterns)]
        work = [(s, l) for s, l in hits if s == 'experience']
        proven = [l for s, l in work if _has_numbers(l)]
        if area in excluded:
            grade = 'Overruled'
        elif proven:
            grade = 'Proven'
        elif work:
            grade = 'Described'
        elif any(s == 'volunteer' for s, _ in hits):
            grade = 'Volunteer'
        elif hits:
            grade = 'Summary'
        elif area in confirmed:
            grade = 'Confirmed'
        else:
            grade = 'Not shown'
        evidence = (proven or [l for _, l in work] or [l for _, l in hits] or [''])[0]
        rows.append({'area': area, 'grade': grade, 'evidence': evidence[:240],
                     'confirmed_by_you': area in confirmed,
                     'expected': area in EXPECTED_FOR_LEADERS})
    rows.sort(key=lambda r: (_GRADE_ORDER.index(r['grade']), r['area']))

    vague = []
    for _section, line in lines:
        for phrase in VAGUE_PHRASES:
            if re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', line, re.I):
                vague.append({'phrase': phrase, 'line': line[:200]})
    seen, unique = set(), []
    for item in vague:
        if item['phrase'] not in seen:
            seen.add(item['phrase'])
            unique.append(item)

    work_bullets = [l for s, l in lines if s == 'experience']
    numbered = sum(_has_numbers(l) for l in work_bullets)
    prompts = []
    by_area = {r['area']: r for r in rows}
    for area in EXPECTED_FOR_LEADERS:
        r = by_area[area]
        if r['grade'] in ('Not shown', 'Summary', 'Volunteer'):
            prompts.append(f"{area}: not shown in your work experience. If true, add a bullet with scale "
                           f"(dollars, people, sites, growth).")
        elif r['grade'] == 'Confirmed':
            prompts.append(f"{area}: you confirmed it, but the resume never says so. Add it; employers only see the resume.")
        elif r['grade'] == 'Described':
            prompts.append(f"{area}: described without numbers. Add the size or result.")
    facts = answers or {}
    for key, label in (('budget_usd', 'budget or revenue size'), ('headcount', 'number of people you lead'),
                       ('sites', 'number of publications or sites')):
        try:
            value = float(facts.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value and str(int(value)) not in str(text or '').replace(',', ''):
            prompts.append(f"Your profile lists a {label} of {int(value):,}, but the resume doesn't state it.")
    return {'areas': rows, 'vague': unique, 'prompts': prompts,
            'work_bullets': len(work_bullets), 'numbered_bullets': numbered,
            'confirmed': sorted(confirmed), 'excluded': sorted(excluded)}
