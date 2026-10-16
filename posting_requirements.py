"""Evidence-limited checks of actual employer minimums and applicant restrictions.

Only text appearing in a vacancy is used. These checks support prioritization,
not determinations of eligibility or whether a résumé holder could obtain
a credential or relocate. Absence of a phrase in the résumé is not proof of
absence of a skill. Preferred conditions are never treated as mandatory.
"""
import re
from html import unescape

INTERNAL_ONLY = re.compile(
    r'\b(?:in[- ]house only|internal (?:applicants|candidates|employees) only|'
    r'only (?:current|existing|internal) (?:employees|staff|applicants|candidates)|'
    r'(?:open|available) (?:only|exclusively) to (?:current|existing|internal) '
    r'(?:employees|staff|applicants|candidates)|'
    r'current employees? (?:only|may apply)|'
    r'(?:applications?|applicants?) (?:are |is )?(?:limited|restricted) '
    r'to (?:current|existing|internal) (?:employees|staff))\b', re.I)
INTERNAL_NEGATION = re.compile(
    r'\b(?:not restricted to|not limited to|open to both|'
    r'internal and external|external and internal)\b', re.I)

RESIDENCY = re.compile(
    r'\b(?:(?:Boston|New York City|NYC|city|county|state|municipal)\s+'
    r'residency\s+(?:is\s+)?(?:required|mandatory)|'
    r'(?:must|required to)\s+(?:be\s+)?(?:a\s+)?'
    r'(?:resident of|reside (?:in|within))\s+[^.;:]{3,75}|'
    r'residency\s+(?:in|within)\s+[^.;:]{3,65}\s+(?:is\s+)?required)\b', re.I)
REQUIRED = re.compile(
    r'\b(?:must|require(?:s|d|ment)?|mandatory|minimum|'
    r'need(?:s|ed)?|essential|at least|qualifications?|'
    r'\d+\+?\s+years?\s+of)\b', re.I)
PREFERRED = re.compile(
    r'\b(?:preferred|ideally|nice to have|desirable|a plus|'
    r'not required|optional|desired but not required)\b', re.I)
FIELD_QUALIFIER = re.compile(
    r'\b(?:experience|knowledge|expertise|background|'
    r'proficiency|certification|license|licence|credential|'
    r'training|skills|portfolio)\b', re.I)
OPPORTUNITY_TO_OBTAIN = re.compile(
    r'\b(?:ability|able|eligible)\s+to\s+(?:obtain|acquire|earn)|'
    r'\b(?:obtain|acquire|earn)\b.{0,42}\b(?:within|by|after)\b', re.I)

# Each rule needs evidence in the *job description* near a qualification
# word; the company industry or role title alone does not create a required
# qualification. A separately confirmed résumé term must be field-specific.
FIELDS = (
    ('Water utilities / transmission operations',
     r'\b(?:water distribution|water treatment|water utility|'
     r'water transmission|drinking water systems?|water operator|'
     r'waterworks|wastewater systems?)\b',
     r'\b(?:water utility operations|water distribution systems?|'
     r'water treatment operator|water transmission engineer|'
     r'water distribution certification)\b',24),
    ('Environmental health and safety / OSHA',
     r'\b(?:environmental health (?:and|&) safety|'
     r'\bEHS\b|\bHSE\b|industrial safety|OSHA compliance|'
     r'OSHA[- ]?(?:10|30)|occupational safety)\b',
     r'\b(?:environmental health (?:and|&) safety|\bEHS\b|'
     r'OSHA safety management|industrial safety|'
     r'occupational safety management)\b',23),
    ('Product / UX design portfolio',
     r'\b(?:product design|UX design|UI design|'
     r'user[- ]experience design|design portfolio|Figma|'
     r'user[- ]interface design)\b',
     r'\b(?:UX design|UI design|product design portfolio|'
     r'product designer|user[- ]experience design|Figma)\b',24),
    ('Construction / skilled building systems',
     r'\b(?:building systems engineering|electrical systems maintenance|'
     r'HVAC systems?|licensed electrician|construction engineering|'
     r'building code enforcement)\b',
     r'\b(?:HVAC systems maintenance|licensed electrician|'
     r'construction engineering|building code enforcement|'
     r'facility systems engineering)\b',22),
    ('Emergency preparedness / incident command',
     r'\b(?:emergency management certification|incident command system|'
     r'\bICS[- ]?[123]\d\d\b|emergency preparedness operations|'
     r'public health emergency preparedness)\b',
     r'\b(?:incident command system|emergency management operations|'
     r'emergency preparedness administration)\b',18),
    ('Specialized public accounting',
     r'\b(?:governmental accounting standards|GASB|'
     r'GAAP accounting|fund accounting|audited financial statements|'
     r'certified public accountant)\b',
     r'\b(?:governmental accounting|GASB|GAAP accounting|'
     r'fund accounting|certified public accountant)\b',19),
    ('Education / instructional credentials',
     r'\b(?:teaching certificate|teaching licen[sc]e|'
     r'curriculum design|instructional leadership credential)\b',
     r'\b(?:teaching certificate|teaching licen[sc]e|'
     r'curriculum design|instructional leadership credential)\b',18),
)

# These are unambiguous job-specific credentials / application artifacts.
CREDENTIALS = (
    ('Water operator certification',
     r'\b(?:water distribution|water treatment|waterworks|wastewater)'
     r'.{0,60}\b(?:certificat(?:e|ion)|licen[sc]e|operator credential)\b',
     r'\b(?:water distribution|water treatment|waterworks|wastewater)'
     r'.{0,60}\b(?:certificat(?:e|ion)|licen[sc]e|operator credential)\b',22),
    ('Engineering professional license',
     r'\b(?:professional engineer(?:ing)?\s+(?:licen[sc]e|registration)|'
     r'PE\s+(?:licen[sc]e|registration)|'
     r'licensed professional engineer)\b',
     r'\b(?:professional engineer(?:ing)?\s+(?:licen[sc]e|registration)|'
     r'PE\s+(?:licen[sc]e|registration))\b',26),
    ('OSHA / EHS certification',
     r'\b(?:OSHA[- ]?(?:10|30)\s*(?:hour)?(?:\s+certificat(?:e|ion))?|'
     r'certified safety professional|CSP certification)\b',
     r'\b(?:OSHA[- ]?(?:10|30)|certified safety professional|'
     r'CSP certification)\b',17),
    ('Professional design portfolio',
     r'\b(?:(?:design|UX|UI|product)\s+portfolio|'
     r'portfolio\s+(?:demonstrating|showcasing)\s+(?:UX|UI|design))\b',
     r'\b(?:UX design portfolio|UI design portfolio|'
     r'product design portfolio|professional design portfolio)\b',22),
)


def _clean(value):
    text=unescape(re.sub(r'<[^>]{0,300}>', ' ', str(value or '')))
    text=re.split(r'\b(?:Similar Jobs|Jobs for you|Recently Viewed Jobs|'
                  r'Top Matches for You|Insights from previous hires)\b',
                  text,maxsplit=1,flags=re.I)[0]
    # Full official bulletins use headings to separate minimum from
    # preferred qualifications. Preserve these boundaries.
    lines=[re.sub(r'[ \t]+',' ',line).strip() for line in text.splitlines()]
    return '\n'.join(line for line in lines if line)[:26000]


def _context(text, found, radius=145):
    return text[max(0,found.start()-radius):min(len(text),found.end()+radius)]


def _clause(text, match):
    # Preserve enough preceding wording to catch "minimum qualifications:"
    # but stop at full stops/semicolons to avoid adjacent unrelated duties.
    lo=max(0,match.start()-115)
    hi=min(len(text),match.end()+90)
    window=text[lo:hi]
    start=match.start()-lo
    preceding=max((window.rfind(c,0,start) for c in '.;!?'),default=-1)
    following=[window.find(c,match.end()-lo) for c in '.;!?']
    following=[v for v in following if v>=0]
    a=preceding+1 if preceding>=0 else 0
    b=min(following) if following else len(window)
    return window[a:b].strip()


_HEADINGS = re.compile(
    r'(?im)^\s*(minimum qualifications?|required qualifications?|qualifications?|'
    r'desired qualifications?|preferred qualifications?|experience and education|'
    r'job responsibilities|position description|duties and responsibilities|'
    r'additional information)\s*:?\s*$')


def _qualification_scope(text, position):
    current=''
    for match in _HEADINGS.finditer(text):
        if match.start()>position:
            break
        current=match.group(1).strip().casefold()
    return current


def _priority(clause, term, section=''):
    if 'desired' in section or 'preferred' in section:
        return 'Preferred / mentioned'
    tail=clause[max(0,term.end()-3):term.end()+95]
    lead=clause[max(0,term.start()-100):term.start()]
    # Only read preference language within the same qualification clause,
    # not from the next heading in a full bulletin.
    nearby_line=clause[max(0,term.start()-80):term.end()+95].split('\n',1)[0]
    if (PREFERRED.search(nearby_line) or
            re.search(r'\b(?:preferred|desirable|nice to have)\b',
                      lead.rsplit('\n',1)[-1][-45:],re.I)):
        return 'Preferred / mentioned'
    if REQUIRED.search(lead) or REQUIRED.search(tail.split('\n',1)[0]):
        return 'Required / minimum — verify exact wording'
    if (section in ('qualifications','qualification',
                    'minimum qualifications','minimum qualification',
                    'required qualifications','required qualification',
                    'experience and education')
            and FIELD_QUALIFIER.search(clause)):
        return 'Required / minimum — employer qualifications section'
    if (FIELD_QUALIFIER.search(clause) and
            re.search(r'\b(?:minimum qualifications|requirements)\b',clause,re.I)):
        return 'Required / minimum — verify exact wording'
    return 'Field expertise mentioned — verify'


def extract_posting_requirements(job, resume=''):
    """Find supported minimum qualification, eligibility and residency checks.

    Only apply substantial ranking cautions to employer text indicating
    required qualifications or an explicit eligibility restriction.
    """
    desc=_clean(job.get('description'))
    title=str(job.get('title') or '')
    resume=_clean(resume)
    checks=[]
    seen=set()
    def add(area,kind,priority,excerpt,penalty,resume_status):
        if area in seen:
            return
        seen.add(area)
        checks.append({
            'area':area,'type':kind,'priority':priority,
            'listing_excerpt':re.sub(r'\s+',' ',excerpt).strip()[:280],
            'resume_status':resume_status,
            'ranking_caution':int(penalty),
        })

    # A title that explicitly states "IN-HOUSE ONLY" is sufficient;
    # descriptions may independently contain a restriction.
    for scope in (title,desc):
        match=INTERNAL_ONLY.search(scope)
        if match and not INTERNAL_NEGATION.search(_context(scope,match,100)):
            add('Internal applicants only','Application eligibility',
                'Explicit restriction — verify eligibility',
                _context(scope,match,85),50,
                'Current employment with this organization not verified; check before applying.')
            break
    for match in list(RESIDENCY.finditer(desc))[:1]:
        clause=_clause(desc,match)
        if re.search(r'\b(?:waived|not required|no residency requirement)\b',
                     clause,re.I):
            continue
        add('Employer residency condition','Residency / location',
            'Required / minimum — verify exact wording',clause,13,
            'Residence or willingness and ability to relocate is not established by the résumé.')

    for area,pattern,evidence,penalty in FIELDS:
        finder=re.compile(pattern,re.I)
        matched=list(finder.finditer(desc))
        if not matched:
            continue
        for match in matched[:6]:
            clause=_clause(desc,match)
            relative_start=max(0,match.start()-(desc.find(clause) if clause else match.start()))
            local=re.search(pattern,clause,re.I)
            if local is None:
                continue
            priority=_priority(clause,local,_qualification_scope(desc,match.start()))
            if (not FIELD_QUALIFIER.search(clause)
                    and priority=='Field expertise mentioned — verify'):
                continue
            has_evidence=bool(re.search(evidence,resume,re.I))
            required=priority.startswith('Required')
            score=(penalty if required and not has_evidence else
                   0 if has_evidence else 0)
            add(area,'Field-specific experience',priority,clause,score,
                'Related specialist field is mentioned in résumé; duties and duration still need verification.'
                if has_evidence else
                'No matching field-specific résumé evidence found; verify before applying.')
            # Once a field is added use the first credible qualification
            break

    for area,pattern,evidence,penalty in CREDENTIALS:
        matches=list(re.finditer(pattern,desc,re.I))
        for match in matches[:5]:
            clause=_clause(desc,match)
            local=re.search(pattern,clause,re.I)
            if not local:
                continue
            priority=_priority(clause,local,_qualification_scope(desc,match.start()))
            if priority=='Preferred / mentioned':
                score=0
            elif priority.startswith('Required'):
                score=penalty
            else:
                score=0
            if OPPORTUNITY_TO_OBTAIN.search(clause):
                priority='May be obtained later — verify deadline'
                score=min(6,score)
            # A textual mention of a credential on a résumé is not proof that
            # it is active; flag verification even where it appears.
            resume_has=bool(re.search(evidence,resume,re.I))
            if resume_has:
                score=0
            add(area,'License / portfolio',priority,clause,score,
                'Related credential mentioned in résumé; verify validity and level.'
                if resume_has else
                'Required credential/portfolio not established by the résumé; verify the exact condition.')
            break
    penalty=min(65,sum(x['ranking_caution'] for x in checks))
    restricted=any(x['area']=='Internal applicants only' for x in checks)
    return {'checks':checks,'ranking_caution':penalty,
            'application_restricted':restricted}
