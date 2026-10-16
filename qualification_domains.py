"""Conservative detection of domain-specific hiring experience from posting text.

Rules flag text for an applicant to verify, not eligibility decisions. A match
to general management years or broadly related job duties does not establish
years of experience in a different professional field.
"""
import re
from html import unescape

# Name, field-specific vocabulary, title keywords (where applicable).
# Deliberately do not equate general "operations", "management" or
# "distribution" with experience in these specialized domains.
DOMAINS = (
    ('Payroll systems / compliance specialization',
     r'\b(?:payroll (?:administration|processing|management|systems|compliance)|payroll tax|time capture systems)\b',
     r'\bpayroll\b'),
    ('Healthcare revenue cycle specialization',
     r'\b(?:revenue cycle|patient billing|patient financial services|medical billing|healthcare reimbursement)\b',
     r'\b(?:revenue cycle|patient billing|patient financial services)\b'),
    ('Merchant payments specialization',
     r'\b(?:payments? (?:operations|processing|acceptance|experience)|merchant (?:acquiring|payments?)|card network|payment gateway)\b',
     r'\b(?:payments? (?:performance|operations|product|strategy)|merchant (?:payments?|acquiring))\b'),
    ('Human resources / employee relations',
     r'\b(?:HR generalist|human resources (?:generalist|experience|management)|'
     r'employee relations (?:experience|background)|HR administration|'
     r'employee lifecycle|COBRA administration|onboarding and offboarding)\b',
     r'\b(?:human resources|HR director|people operations)\b'),
    ('K-12 / school operations',
     # The word "education" alone is not school-operating experience: MBA
     # requirements and advanced business education must not trigger K-12.
     r'\b(?:K[- ]?12 (?:school )?(?:operations|education|school leadership)'
     r'(?: experience| background| administration)?|'
     r'school[- ]based operations leadership(?: experience| role)?|'
     r'school operations(?: experience| management| leadership)?|'
     r'charter school (?:operations|experience|leadership)|'
     r'school (?:administration|leadership)|'
     r'(?:managing |executive )?director of school operations)\b',
     r'\b(?:K[- ]?12|school operations|director of school|'
     r'school (?:director|administrator)|principal)\b'),
    ('Construction / engineering operations',
     r'\b(?:construction (?:[a-z-]+\s+){0,3}(?:experience|operations|management|industry|services|'
     r'projects?|field teams?)|engineering (?:services|operations|industry))\b',
     r'\b(?:construction|engineering services)\b'),
    ('Food handling / safety / distribution',
     r'\b(?:food handling(?: environments?)?|food[- ]service (?:operations|experience)|'
     r'food safety(?: standards?|experience|program)?|HACCP|SQF|FSMA|'
     r'cold chain|food distribution experience)\b',
     r'\b(?:food distribution|food services?|restaurant|Sbarro|Taco Bell|Dunkin|Subway)\b'),
    ('Fuel retail / convenience stores',
     r'\b(?:fuel (?:station|handling|retail|storage|operations)|'
     r'convenience[- ]store(?: operations| management)?|travel[- ]center'
     r'(?: operations| management)?|fuel,?\s+convenience[- ]store)\b',
     r'\b(?:travel center|fuel station|convenience store)\b'),
    ('Restaurant / food-service management',
     r'\b(?:restaurant (?:management|operations|experience|environment)|'
     r'quick[- ]service restaurant|fast[- ]casual (?:restaurant|environment)|'
     r'full[- ]service (?:restaurant|dining|diner)(?: experience| management)?|'
     r'casual dining(?: experience| management)?|diner (?:management|environment)|'
     r'food[- ]service management|restaurant[- ]management experience)\b',
     r'\b(?:restaurant|(?:Black Bear|other) Diner|diner|Sbarro|Taco Bell|'
     r'Dunkin|Subway|fast food|full[- ]service dining)\b'),
    ('Enterprise B2B sales / quota management',
     r'\b(?:enterprise B2B sales|enterprise (?:sales|selling|business development)|'
     r'quota[- ]carrying|new[- ]logo bookings|complex enterprise (?:deals|sales)|'
     r'solution sales|multi[- ]year managed[- ]services (?:sales|contracts))\b',
     r'\b(?:enterprise sales|B2B sales|business development)\b'),
    ('Warehouse / industrial operations',
     r'\b(?:warehouse (?:management|operations|experience)|'
     r'distribution (?:center|facility|warehouse)|industrial operations|'
     r'industrial manufacturing experience|trucking (?:operations|fleet))\b',
     r'\b(?:warehouse|industrial|manufacturing)\b'),
    ('Public transit / fleet operations',
     r'\b(?:public transport(?:ation)? (?:management|operations|organization|experience)|'
     r'multimodal transit|multi[- ]modal transit|paratransit|transit agency|'
     r'fixed[- ]route transit|fleet operations)\b',
     r'\b(?:transit|public transportation|fleet)\b'),
    ('Correctional facility operations',
     r'\b(?:correctional (?:facility|services|operations)|'
     r'commissary (?:operations|management)|detention facility|prison operations)\b',
     r'\b(?:correctional|commissary|detention)\b'),
    ('Facilities / custodial management',
     r'\b(?:facilit(?:y|ies) management|janitorial|custodial|'
     r'building maintenance|facilities maintenance)\b',
     r'\b(?:custodial|janitorial|facilities)\b'),
    ('Property / residential operations',
     r'\b(?:property (?:management|operations|manager(?:s)?|performance)|'
     r'residential propert(?:y|ies)|residential community|'
     r'rental (?:operations|propert(?:y|ies)|management|software)|'
     r'student (?:housing|accommodation|living)|'
     r'leasing (?:operations|experience|activities|inquiries)|'
     r'lease (?:renewals|applications|administration)|'
     r'rent (?:collections?|payments?)|resident (?:accounts|retention|relations|records)|'
     r'property management software|(?:housing|rental) occupancy|'
     r'occupancy (?:rates|management))\b',
     r'\b(?:HOA|COA|property|residential|leasing|student housing|'
     r'student accommodation)\b'),
    ('Clinical / healthcare operations',
     r'\b(?:healthcare administration|hospital management|clinical operations|'
     r'medical practice management|patient care operations)\b',
     r'\b(?:clinical|hospital|medical)\b'),
    ('Insurance / risk management',
     r'\b(?:commercial insurance|insurance portfolio|'
     r'self[- ]insurance|contractual risk transfer|claims administration|'
     r'professional risk management)\b',
     r'\b(?:risk management|insurance)\b'),
    ('Product marketing / go-to-market',
     r'\b(?:product marketing|go[- ]to[- ]market|commercialization|'
     r'product launch experience)\b',
     r'\b(?:product marketing|go[- ]to[- ]market)\b'),
    ('SaaS / marketplace operations',
     r'\b(?:SaaS (?:operations|experience|industry)|'
     r'software[- ]as[- ]a[- ]service|partner marketplace|'
     r'digital marketplace operations|revenue operations)\b',
     r'\b(?:SaaS|marketplace|revenue operations)\b'),
    ('Professional / regulated services management',
     r'\b(?:legal services (?:management|experience)|'
     r'professional services (?:environment|experience|operations)|'
     r'regulated (?:services?|industry|environment))\b',
     r'\b(?:law firm|legal services|professional services)\b'),
)
COMPILED = tuple((label, re.compile(phrase, re.I),
                  re.compile(title, re.I)) for label,phrase,title in DOMAINS)
YEARS = re.compile(r'\b(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)'
                   r'(?:\s*[-–]\s*\d{1,2})?\+?\s+years?\b', re.I)
REQUIRED = re.compile(r'\b(?:required|requires?|must (?:have|possess)|minimum|'
                      r'essential|needed|necessary)\b', re.I)
PREFERRED = re.compile(r'\b(?:preferred|strongly preferred|desirable|'
                       r'nice to have|a plus|a bonus)\b', re.I)
EXPERIENCE = re.compile(r'\b(?:experience|background|expertise)\b', re.I)
# Duty-language alone can be relevant without making something a mandatory
# qualification. Only use explicit operating responsibilities close to the
# subject, not incidental mention of an industry as a client or partner.
ROLE_DUTY = re.compile(
    r'\b(?:manage|managing|oversee|overseeing|lead|leading|operate|operating|'
    r'administer|administering|coordinate|coordinating|handle|handling|'
    r'support(?:ing)?)\b', re.I)


def clean_posting(text):
    text = unescape(re.sub(r'<[^>]{0,200}>', ' ', str(text or '')))
    text = re.split(r'\b(?:Similar Jobs|Jobs for you|Recently Viewed Jobs|'
                    r'Top Matches for You|Insights from previous hires)\b',
                    text, maxsplit=1, flags=re.I)[0]
    return re.sub(r'\s+', ' ', text)[:26000].strip()


def _excerpt(text, match, radius=115):
    start=max(0,match.start()-radius)
    end=min(len(text),match.end()+radius)
    return (('…' if start else '')+text[start:end].strip()+
            ('…' if end<len(text) else ''))[:280]


def _closest_indicator(text, position, regex, radius=105):
    window=text[max(0,position-radius):min(len(text),position+radius)]
    offsets=[abs(max(0,position-radius)+m.start()-position)
             for m in regex.finditer(window)]
    return min(offsets) if offsets else None


def _years_near_domain(text, match):
    window=text[max(0,match.start()-140):min(len(text),match.end()+110)]
    for years in YEARS.finditer(window):
        # Nearby duration must be framed as experience; "100 years serving" is not.
        around=window[max(0,years.start()-25):min(len(window),years.end()+125)]
        if (EXPERIENCE.search(around) or
                re.search(r'\byears?\s+of\b',around,re.I) or
                re.search(r'\b(?:management|operations)\b',around,re.I)):
            return True
    return False


# The same posting can require school-based leadership while only
# *preferring* K-12 industry tenure. Score only the mandatory experience
# as required; broad "required" or "years" elsewhere in the posting must
# not transfer to K-12 education by proximity.
SCHOOL_BASED_LEADERSHIP = re.compile(
    r'\b(?:experience(?: and results)? in (?:a )?school[- ]based operations '
    r'leadership (?:role|position)|school[- ]based operations leadership '
    r'(?:experience|role)|school operations leadership experience)\b', re.I)
SCHOOL_K12_PREFERRED = re.compile(
    r'\bK[- ]?12 education experience\s+(?:strongly\s+)?preferred\b', re.I)
LOCAL_PREFERENCE = re.compile(
    r'^[\s,:;()\-]*(?:strongly\s+)?(?:preferred|desirable)\b', re.I)
LOCAL_REQUIREMENT = re.compile(
    r'^[\s,:;()\-]*(?:required|mandatory|essential)\b', re.I)
MINIMUM_IN_FIELD = re.compile(
    r'\b(?:minimum|at least|must have|requires?)\b.{0,75}'
    r'\b(?:school operations|school[- ]based operations|K[- ]?12)\b', re.I)


def _school_priority(desc, matches, title_match):
    """Classify a *school-related clause*, never unrelated academic degrees.

    School-based operational leadership can be required even when an
    explicit K-12 teaching/sector history is only preferred.
    """
    preferred_school_background=bool(SCHOOL_K12_PREFERRED.search(desc))
    mandatory_school_leadership=None
    for school_role in SCHOOL_BASED_LEADERSHIP.finditer(desc):
        leading=desc[max(0,school_role.start()-170):school_role.start()]
        trailing=desc[school_role.end():school_role.end()+45]
        if LOCAL_PREFERENCE.match(trailing):
            continue
        if (re.search(r'\b(?:Must Have|Required Qualifications|Minimum Qualifications)\s*:',
                      leading,re.I) or LOCAL_REQUIREMENT.match(trailing)
                or re.search(r'\b(?:required|must have)\b',leading[-48:],re.I)):
            mandatory_school_leadership=school_role
            break
    if mandatory_school_leadership is not None:
        wording=('Required school-based operations leadership; '
                 'K-12 sector experience preferred' if preferred_school_background
                 else 'Required school-based operations leadership')
        return wording,23,True,mandatory_school_leadership
    for match in matches:
        trailing=desc[match.end():match.end()+35]
        if LOCAL_PREFERENCE.match(trailing):
            return 'Preferred experience',5,False,match
        if LOCAL_REQUIREMENT.match(trailing):
            return 'Required / experience stated — verify exact wording',23,True,match
    if MINIMUM_IN_FIELD.search(desc):
        return 'Required / experience stated — verify exact wording',23,True,matches[0] if matches else None
    if title_match:
        return 'Specialized role or field — verify experience',11,False,matches[0] if matches else None
    if matches:
        return 'Experience mentioned — review full posting',10,False,matches[0]
    return 'Role responsibility — verify relevant experience',8,False,None


def identify_specialized_requirements(job, resume=''):
    """Report documented posting domain cues; never infer eligibility."""
    title=str(job.get('title') or '')
    desc=clean_posting(job.get('description'))
    resume=clean_posting(resume)
    results=[]
    for name, phrase, title_pattern in COMPILED:
        matches=list(phrase.finditer(desc))
        title_match=bool(title_pattern.search(title))
        if not matches and not title_match:
            continue
        match=matches[0] if matches else None
        # Domain words in a title without any backing detail are still worth
        # examining, but not grounds for declaring a formal requirement.
        years=any(_years_near_domain(desc,m) for m in matches[:6])
        required_distance=min((x for x in
            (_closest_indicator(desc,m.start(),REQUIRED,85) for m in matches[:6])
            if x is not None),default=None)
        preferred_distance=min((x for x in
            (_closest_indicator(desc,m.start(),PREFERRED,85) for m in matches[:6])
            if x is not None),default=None)
        # A specialist domain must have actual job-posting context. A stray
        # reference to marketing, customer service or a vendor isn't sufficient.
        experience_near=any(
            _closest_indicator(desc,m.start(),EXPERIENCE,65) is not None
            for m in matches[:6])
        duty_near=any(
            _closest_indicator(desc,m.start(),ROLE_DUTY,70) is not None
            for m in matches[:6])
        if not (years or required_distance is not None or
                preferred_distance is not None or title_match or
                experience_near or duty_near):
            continue
        if name=='K-12 / school operations':
            priority, penalty, required_context, school_match = (
                _school_priority(desc,matches,title_match))
            if school_match is not None:
                match=school_match
        elif preferred_distance is not None and (
                required_distance is None or preferred_distance<required_distance):
            priority='Preferred experience'
            penalty=5
        elif years or required_distance is not None:
            priority='Required / experience stated — verify exact wording'
            penalty=23
        elif title_match:
            priority='Specialized role or field — verify experience'
            penalty=11
        elif experience_near:
            priority='Experience mentioned — review full posting'
            penalty=10
        else:
            priority='Role responsibility — verify relevant experience'
            penalty=8
        if name!='K-12 / school operations':
            required_context=bool(years or required_distance is not None)
        related=bool(phrase.search(resume))
        if related:
            status='Related field terms appear in resume; domain-specific responsibilities and years remain unverified'
            penalty=0
        else:
            status='Field-specific experience not documented in resume; not proof the applicant lacks it'
        excerpt=(_excerpt(desc,match) if match
                 else 'The job title refers to '+name.lower())
        results.append({'area':name,'listing_excerpt':excerpt,'priority':priority,
                        'required_context':required_context,
                        'mentioned_in_title':title_match,
                        'resume_status':status,'needs_verification':not related,
                        'ranking_caution':penalty})
    # Avoid swamping the fit score when overlapping specialties are listed.
    return sorted(results,key=lambda r:(-r['ranking_caution'],r['area']))[:6]
