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
    ('Human resources / employee relations',
     r'\b(?:HR generalist|human resources (?:generalist|experience|management)|'
     r'employee relations (?:experience|background)|HR administration|'
     r'employee lifecycle|COBRA administration|onboarding and offboarding)\b',
     r'\b(?:human resources|HR director|people operations)\b'),
    ('K-12 / school operations',
     r'\b(?:K[- ]?12 (?:school )?operations|school operations experience|'
     r'charter school operations|education administration|school administration)\b',
     r'\b(?:K[- ]?12|school (?:director|administrator)|principal)\b'),
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
    return re.sub(r'\s+', ' ', text)[:16000].strip()


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
        if preferred_distance is not None and (
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
        related=bool(phrase.search(resume))
        if related:
            status='Related field terms appear in resume; domain-specific responsibilities and years remain unverified'
            penalty=0
        else:
            status='Field-specific experience not documented in resume; not proof the applicant lacks it'
        excerpt=(_excerpt(desc,match) if match
                 else 'The job title refers to '+name.lower())
        results.append({'area':name,'listing_excerpt':excerpt,'priority':priority,
                        'required_context':bool(years or required_distance is not None),
                        'mentioned_in_title':title_match,
                        'resume_status':status,'needs_verification':not related,
                        'ranking_caution':penalty})
    # Avoid swamping the fit score when overlapping specialties are listed.
    return sorted(results,key=lambda r:(-r['ranking_caution'],r['area']))[:6]
