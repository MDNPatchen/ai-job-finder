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
TRANSFER_ONLY_TITLE = re.compile(
    r'\b(?:internal\s+)?transfers?\s+only\b', re.I)
TRANSFER_ONLY_APPLICATION = re.compile(
    r'\b(?:applicants?|candidates?|employees?|staff)\b.{0,65}'
    r'\b(?:internal\s+)?transfers?\s+only\b|'
    r'\b(?:internal\s+)?transfers?\s+only\b.{0,65}'
    r'\b(?:applicants?|candidates?|employees?|staff)\b', re.I)
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
    ('Compensation and equity administration',
     r'\b(?:compensation (?:and|&)\s*equity|'
     r'compensation (?:programs?|benchmarking|strateg(?:y|ies)|'
     r'analysis|administration)|equity compensation|'
     r'(?:stock options?|equity awards?)\s+(?:administration|plans?)|'
     r'total rewards|pay equity|salary bands?)\b',
     r'\b(?:compensation (?:and|&)\s*equity|'
     r'compensation (?:programs?|benchmarking|strateg(?:y|ies)|'
     r'analysis|administration)|equity compensation|'
     r'(?:stock options?|equity awards?)\s+(?:administration|plans?)|'
     r'total rewards|pay equity)\b',22),
    ('Analytical laboratory mass spectrometry',
     r'\b(?:LC[- ]?MS/?MS|mass spectrometr(?:y|ic)|'
     r'bioanalytical testing|chromatograph\w*|'
     r'analytical chemistry|laboratory (?:scientist|method development))\b',
     r'\b(?:LC[- ]?MS/?MS|mass spectrometr(?:y|ic)|'
     r'bioanalytical testing|chromatograph\w*|'
     r'analytical chemistry|laboratory (?:scientist|method development))\b',30),
    ('IT-specific project delivery',
     r'\b(?:IT project management|technology project management|'
     r'software implementation projects?|systems integrations?|'
     r'enterprise IT (?:infrastructure|projects?)|'
     r'information technology projects?|technical project management)\b',
     r'\b(?:IT project management|technology project management|'
     r'software implementation projects?|systems integrations?|'
     r'enterprise IT (?:infrastructure|projects?)|'
     r'information technology projects?|technical project management)\b',23),
    ('Advanced marketing science / statistical modeling',
     r'\b(?:marketing science|marketing mix model(?:ing|ling)|'
     r'econometric modeling|statistical programming|'
     r'causal inference modeling|incrementality testing)\b',
     r'\b(?:marketing science|marketing mix model(?:ing|ling)|'
     r'econometric modeling|statistical programming|'
     r'causal inference modeling|incrementality testing)\b',22),
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
    # Employers can supply raw HTML OR entity-escaped HTML. Unescape *before*
    # stripping tags so <h3>What You're Great At</h3> stays a section header.
    text=str(value or '')
    for _ in range(2):
        newer=unescape(text)
        if newer==text:
            break
        text=newer
    # Preserve HTML list items, headings and paragraph boundaries; without
    # these, a required design background may be mistaken for a preference
    # from a nearby, unrelated sentence.
    text=re.sub(r'(?is)<\s*(?:br|hr)\b[^>]*>', '\n', text)
    text=re.sub(r'(?is)<\s*/?\s*(?:h[1-6]|p|li|ul|ol|div|section|'
                r'header|strong|b)\b[^>]*>', '\n', text)
    text=re.sub(r'(?is)<[^>]{0,350}>', ' ', text)
    text=re.split(r'\b(?:Similar Jobs|Jobs for you|Recently Viewed Jobs|'
                  r'Top Matches for You|Insights from previous hires)\b',
                  text,maxsplit=1,flags=re.I)[0]
    lines=[re.sub(r'\s+',' ',line.replace('\xa0',' ')).strip()
           for line in text.splitlines()]
    return '\n'.join(line for line in lines if line)[:26000]


def _context(text, found, radius=145):
    return text[max(0,found.start()-radius):min(len(text),found.end()+radius)]


def _clause(text, match):
    # Bullet boundaries matter. If qualifications appear in consecutive <li>
    # items, don't let a preferred requirement negate the preceding minimum.
    lo=max(0,match.start()-145)
    hi=min(len(text),match.end()+145)
    window=text[lo:hi]
    start=match.start()-lo
    end=match.end()-lo
    preceding=max((window.rfind(ch,0,start) for ch in '.;!?\n'),default=-1)
    following=[window.find(ch,end) for ch in '.;!?\n']
    following=[pos for pos in following if pos>=0]
    return window[preceding+1 if preceding>=0 else 0:
                  min(following) if following else len(window)].strip()


# Private ATS platforms use different labels for the applicant criteria.
# These match a standalone line only, not casual phrases in job duties.
_HEADINGS = re.compile(
    r"(?im)^\s*((?:(?:minimum|basic|required|desired|preferred)\s+)?"
    r"qualifications?(?:\s*(?:&|and)\s*(?:skills|experience))?|"
    r"experience\s*(?:&|and)\s*(?:education|qualifications?|skills)|"
    r"requirements?(?:\s*(?:&|and)\s*(?:qualifications?|skills))?|"
    r"what\s+(?:you[’']ll|we)\s+(?:need|bring|look\s+for|expect)"
    r"(?:\s+(?:from\s+you|to\s+the\s+team))?|"
    r"what\s+you[’']re\s+great\s+at|"
    r"what\s+you\s+(?:bring|need)\s+to\s+(?:the\s+)?(?:table|team|role)|"
    r"who\s+you\s+are|"
    r"(?:nice\s+to\s+have|preferred\s+(?:experience|skills)|"
    r"desired\s+(?:experience|skills)|bonus\s+points)|"
    r"(?:job\s+)?responsibilities|position\s+description|"
    r"duties\s+and\s+responsibilities|additional\s+information|"
    r"what\s+you[’']ll\s+do|about\s+the\s+(?:role|job))\s*:?\s*$")


def _qualification_scope(text, position):
    current=''
    for match in _HEADINGS.finditer(text):
        if match.start()>position:
            break
        current=match.group(1).strip().casefold()
    return current


def _priority(clause, term, section=''):
    section=section.casefold()
    if re.search(r'\b(?:desired|preferred|nice to have|bonus)\b',section):
        return 'Preferred / mentioned'
    # Work within ONE item, never borrow a "preferred" from the next bullet.
    nearby=clause[max(0,term.start()-105):term.end()+120]
    if PREFERRED.search(nearby):
        return 'Preferred / mentioned'
    if REQUIRED.search(clause):
        return 'Required / minimum — verify exact wording'
    if re.search(
        r'\b(?:qualifications?|requirements?|what you.ll need|'
        r'what we need|what you.ll bring|what we look for|'
        r'what you.re great at|who you are|'
        r'experience and education|experience and qualifications|'
        r'experience and skills|what you bring to)\b',section):
        return 'Required / minimum — employer applicant-criteria section'
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
        match=(INTERNAL_ONLY.search(scope) or
               (TRANSFER_ONLY_TITLE.search(scope) if scope==title else
                TRANSFER_ONLY_APPLICATION.search(scope)))
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
        # The first mention is often a responsibility. Prefer the strongest
        # *applicant qualification* later in the advertisement. An early
        # "deliver EHS training" must not mask "five years of EHS experience".
        candidates=[]
        for match in list(re.finditer(pattern,desc,re.I))[:35]:
            clause=_clause(desc,match)
            local=re.search(pattern,clause,re.I)
            if local is None:
                continue
            section=_qualification_scope(desc,match.start())
            priority=_priority(clause,local,section)
            if (priority=='Field expertise mentioned — verify'
                    and not FIELD_QUALIFIER.search(clause)):
                continue
            weight=(2 if priority.startswith('Required') else
                    1 if priority=='Field expertise mentioned — verify' else 0)
            # Within equivalent priority prefer a clause explicitly stating
            # years or specialized experience to make the explanation useful.
            weight2=bool(re.search(
                r'\b(?:\d+\+?\s*years?|experience|expertise|portfolio|'
                r'certification|proficiency)\b',clause,re.I))
            candidates.append((weight,int(weight2),match.start(),priority,clause))
        if not candidates:
            continue
        _,_,_,priority,clause=max(candidates,key=lambda x:(x[0],x[1],-x[2]))
        has_evidence=bool(re.search(evidence,resume,re.I))
        score=penalty if priority.startswith('Required') and not has_evidence else 0
        add(area,'Field-specific experience',priority,clause,score,
            'Related specialist field is mentioned in résumé; duties and duration still need verification.'
            if has_evidence else
            'No matching field-specific résumé evidence found; verify before applying.')

    for area,pattern,evidence,penalty in CREDENTIALS:
        candidates=[]
        for match in list(re.finditer(pattern,desc,re.I))[:25]:
            clause=_clause(desc,match)
            local=re.search(pattern,clause,re.I)
            if not local:
                continue
            priority=_priority(clause,local,_qualification_scope(desc,match.start()))
            if OPPORTUNITY_TO_OBTAIN.search(clause):
                priority='May be obtained later — verify deadline'
            weight=(3 if priority.startswith('Required') else
                    2 if priority.startswith('May be obtained later') else
                    1 if priority=='Field expertise mentioned — verify' else 0)
            candidates.append((weight,-match.start(),priority,clause))
        if not candidates:
            continue
        _,_,priority,clause=max(candidates,key=lambda x:(x[0],x[1]))
        score=(penalty if priority.startswith('Required') else
               min(6,penalty) if priority.startswith('May be obtained later') else 0)
        resume_has=bool(re.search(evidence,resume,re.I))
        if resume_has:
            score=0
        add(area,'License / portfolio',priority,clause,score,
            'Related credential mentioned in résumé; verify validity and level.'
            if resume_has else
            'Required credential/portfolio not established by the résumé; verify the exact condition.')

    penalty=min(65,sum(x['ranking_caution'] for x in checks))
    restricted=any(x['area']=='Internal applicants only' for x in checks)
    return {'checks':checks,'ranking_caution':penalty,
            'application_restricted':restricted}
