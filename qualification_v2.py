"""Free, explainable qualification checks and industry-specific fit cues.

Only compare source text to uploaded resume. A flagged requirement is NOT a
finding that someone cannot perform a job. No inferences about protected traits.
Use requirement excerpts to explain uncertainty, not hard job exclusions.
"""
import re
from qualification_domains import identify_specialized_requirements
from transfer_fit import transfer_fit
from career_fit_guardrails import evaluate_career_fit
from posting_requirements import extract_posting_requirements
from formal_qualification_guardrails import extract_formal_minimums
from specialist_caution_calibration import calibrate_cautions

_NUMBER = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
           'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
           'eleven': 11, 'twelve': 12, 'fifteen': 15, 'twenty': 20}
_YEAR = re.compile(
    r'\b(?P<amount>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|'
    r'eleven|twelve|fifteen|twenty)(?:\s*\(\s*\d{1,2}\s*\))?'
    r'(?:\s*[-–]\s*\d{1,2})?\+?\s+years?\b', re.I)
_DEGREE = re.compile(
    r'\b(?:bachelor(?:[’\x27]s)?|master(?:[’\x27]s)?|associate(?:[’\x27]s)?|'
    r'baccalaureate|doctoral|doctorate)\s*(?:degree)?\b|'
    r'\b(?:M\.?B\.?A\.?|J\.?D\.?)\b', re.I)
_LICENSE = re.compile(
    r'\b(?:valid (?:[A-Z][a-z]+\s+)?driver(?:[’\x27]s)? licen[sc]e|'
    r'(?:registered|licensed)\s+(?:nurs(?:e|ing)|physician|attorney)|'
    r'RN\s+licen[sc]e|(?:current|active)\s+(?:RN|CPA|PMP)\b|'
    r'(?:certified public accountant|professional engineer)|'
    r'\b(?:CPA|PMP)\s+(?:certification|credential|license))\b', re.I)
_CIVIL = re.compile(
    r'\b(?:must\s+be\s+permanent\s+in\s+(?:the\s+)?(?:civil\s+service\s+)?title|'
    r'only\s+applicants\s+.*?\bpermanent\s+in\s+(?:the\s+)?title|'
    r'permanent\s+civil\s+service\s+status\s+(?:in|as)\b)', re.I)
_RESIDENCY = re.compile(
    r'\b(?:New York City|NYC|city|county|state)\s+residency\s+(?:is\s+)?required\b', re.I)

# Domain terms have to be in the posting, not simply assumed from the employer.
# Higher caution for explicit specialized career requirements in the job text.
DOMAINS = (
    ('Public transit / fleet operations',
     r'\b(?:public transit|public transportation|multimodal transit|multi-modal transit|'
     r'transit agenc\w*|paratransit|fixed[- ]route (?:bus|transit)|fleet operations)\b',
     r'\b(?:transportation director|transit|transportation|fleet)\b'),
    ('Restaurant / food-service management',
     r'\b(?:restaurant management|restaurants?|fast[- ]casual|food safety|'
     r'quick[- ]service restaurant|hospitality kitchen|food[- ]service)\b',
     r'\b(?:restaurant|taco bell|dunkin|subway|food service)\b'),
    ('Facilities / janitorial management',
     r'\b(?:facility management|facilities management|janitorial|custodial|'
     r'building maintenance|facilities maintenance)\b',
     r'\b(?:facility|facilities|janitorial|custodial|building manager)\b'),
    ('Correctional facility operations',
     r'\b(?:correctional facilit\w*|prison operations?|correctional services|'
     r'commissary operations?|detention facilit\w*)\b',
     r'\b(?:commissary|correctional|detention)\b'),
    ('Commercial insurance / risk management',
     r'\b(?:commercial insurance|insurance portfolio|self[- ]insurance|'
     r'contractual risk transfer|claims administration|risk management)\b',
     r'\b(?:risk|insurance|claims)\b'),
    ('Product marketing / go-to-market',
     r'\b(?:product marketing|commercialization|go[- ]to[- ]market|product launches?)\b',
     r'\b(?:product marketing|product manager)\b'),
    ('SaaS / digital marketplace operations',
     r'\b(?:marketplace operations|partner marketplace|software[- ]as[- ]a[- ]service|'
     r'SaaS|revenue operations|product[- ]led growth)\b',
     r'\b(?:marketplace|SaaS|revenue operations)\b'),
    ('Property / residential management',
     r'\b(?:residential propert\w*|property management|community management|'
     r'occupancy rates|real estate portfolio)\b',
     r'\b(?:property|residential|community operations)\b'),
    ('Healthcare administration',
     r'\b(?:hospital administration|healthcare administration|clinical operations|'
     r'health system management|medical practice management)\b',
     r'\b(?:hospital|healthcare|clinical|medical)\b'),
    ('Government financial administration',
     r'\b(?:municipal finance|public finance|government budgeting|'
     r'public[- ]sector financial|governmental accounting)\b',
     r'\b(?:city|county|municipal|public|government)\b'),
)

_ROLE_PATTERNS = (
    (r'\b(?:director of operations|operations director|vp of operations|'
     r'vice president of operations|regional operations director)\b', 97),
    (r'\b(?:chief operating officer|chief administrative officer|\bcoo\b)\b', 93),
    (r'\b(?:deputy|assistant)\s+(?:city|county)\s+manager\b', 89),
    (r'\b(?:city|county)\s+(?:manager|administrator)\b', 88),
    (r'\b(?:group publisher|publisher|general manager)\b', 87),
    (r'\b(?:regional|district|area)\s+(?:director|manager)\b', 80),
    (r'\b(?:director of|director,|communications director)\s+'
     r'(?:communications|marketing|business development|strategic partnerships)\b', 91),
    (r'\b(?:director|head|vice president)\b', 80),
    (r'\b(?:operations|business development|program)\s+manager\b', 69),
    (r'\b(?:marketing|project|product)\s+manager\b', 58),
    (r'\bmanager\b', 57),
)


def _around(text, match, radius=100):
    left=max(0,match.start()-radius)
    right=min(len(text),match.end()+radius)
    return (('…' if left else '') + re.sub(r'\s+', ' ',text[left:right]).strip()
            + ('…' if right<len(text) else ''))[:290]


def _evidence_status(resume, pattern):
    return ('Related term appears in resume; verify the actual credential and relevance'
            if pattern.search(resume) else
            'Not verified from resume; absence of wording does not establish ineligibility')


def _requirement_priority(context):
    if re.search(r'\b(?:preferred|desirable|nice to have|a plus|ideal candidate)\b', context, re.I):
        return 'Preferred / mentioned'
    if re.search(r'\b(?:required|requires?|must|minimum|essential|qualification|only applicants)\b',
                 context, re.I):
        return 'Possibly required — check exact posting'
    return 'Listed — check job description'


def extract_requirements(description, resume=''):
    """Only report phrases visibly present in the posting, never invent credentials."""
    body=re.sub(r'\s+', ' ',str(description or ''))[:26000]
    # Career sites append unrelated job recommendations. Do not interpret
    # those titles (especially RN/nurse jobs) as this role's credentials.
    body=re.split(r'\b(?:Similar Jobs|Jobs for you|Recently Viewed Jobs|'
                  r'Top Matches for You|Insights from previous hires)\b',
                  body,maxsplit=1,flags=re.I)[0]
    resume=str(resume or '')
    results=[]
    seen=set()

    def add(category, match, status, penalty=0):
        excerpt=_around(body,match,95)
        key=(category,excerpt.casefold())
        if key in seen:return
        seen.add(key)
        nearby=body[max(0,match.start()-90):min(len(body),match.end()+90)]
        priority=_requirement_priority(nearby)
        results.append({'type':category,'listing_excerpt':excerpt,'priority':priority,
                        'resume_status':status,'verification_penalty':penalty})

    for match in list(_DEGREE.finditer(body))[:3]:
        # "bachelor" by itself in unrelated text is too weak.
        if not re.search(r'\bdegree\b|\bMBA\b|\bJD\b|\bJuris\b',body[match.start():match.end()+30],re.I):
            continue
        add('Education',match,_evidence_status(resume,_DEGREE))

    for match in list(_LICENSE.finditer(body))[:3]:
        add('License / certification',match,_evidence_status(resume,_LICENSE),11)

    for match in list(_YEAR.finditer(body))[:5]:
        # Ignore years-of-company-history and generic marketing boilerplate.
        surrounding=body[max(0,match.start()-65):min(len(body),match.end()+130)]
        if not re.search(r'\b(?:experience|management|leadership|qualified|qualification|'
                         r'required|minimum|supervisory|professional duties)\b',
                         surrounding,re.I):
            continue
        # The number matters, but total career length is not proof of the
        # specific domain experience stated in this ad.
        token=match.group('amount').lower()
        needed=int(token) if token.isdigit() else _NUMBER.get(token,0)
        if not needed:continue
        broad=re.findall(_YEAR,resume)
        years=[int(y) if y.isdigit() else _NUMBER.get(y.lower(),0) for y in broad]
        if years and max(years)>=needed:
            status=('Resume mentions at least this many total career years; '
                    'the specific field, duties and years in that field are not verified')
        else:
            status='Not verified from resume: number of years and related duties are unknown'
        add('Experience duration',match,status)

    for match in list(_CIVIL.finditer(body))[:2]:
        add('Civil-service eligibility',match,
            'Permanent civil-service status not established by the uploaded resume',19)

    for match in list(_RESIDENCY.finditer(body))[:2]:
        add('Residency condition',match,'Review whether you meet the location/residency rule',0)

    for match in list(re.finditer(r'\b(?:available|respond|on.call)\s+(?:for\s+)?'
                                  r'(?:24\s*/\s*7|twenty[- ]four\s*/\s*seven)\b',
                                  body,re.I))[:1]:
        add('Work schedule / emergency availability',match,
            'Confirm your ability to meet this schedule',0)
    return results[:15]


def assess_specialized_experience(job, resume=''):
    """Use focused, text-supported industry experience cues."""
    return identify_specialized_requirements(job, resume)


def role_alignment(title):
    """How close the role family is to broad publisher/director experience."""
    text=str(title or '')
    if re.search(r'\b(?:restaurant|taco bell|dunkin|subway)\b',text,re.I):
        return 43
    if re.search(r'\b(?:commissary|custodial|janitorial)\b',text,re.I):
        return 48
    if re.search(r'\b(?:risk management|clinical|licensed|insurance)\b',text,re.I):
        return 65
    for pattern,val in _ROLE_PATTERNS:
        if re.search(pattern,text,re.I):
            return val
    return 48


def recalibrate_match(job, qualification, resume_text=''):
    """Transparent comparative research ordering, never eligibility probability."""
    alignment=role_alignment(job.get('title'))
    if not qualification.get('resume_present'):
        return {'index':0,'role_alignment':alignment,
                'cautions':[],'specialties':[],
                'career_fit_cautions':[], 'career_fit_penalty':0,
                'posting_requirement_checks':[], 'posting_requirement_penalty':0,
                'application_restricted':False,
                'transferable_strengths':[], 'duty_coverage':0,
                'confidence':'No resume uploaded'}
    specialties=assess_specialized_experience(job,resume_text)
    cautions=[]
    for item in specialties:
        if item['needs_verification']:
            cautions.append(item.get('priority','Verify experience')+': '+item['area'])
    # Formal employer requirements are independent of title-level or
    # generalized specialist-domain evidence. Count overlapping experience
    # ONLY once, while preserving degree/license and application cautions.
    restrictions=[r for r in qualification.get('screeners',[])
                  if r['type'] in ('License / certification','Civil-service eligibility')
                  and r['resume_status'].startswith(('Not verified','Permanent')) and
                  r['priority']!='Preferred / mentioned']
    credential_penalty=min(20,sum(int(r.get('verification_penalty') or 0)
                                  for r in restrictions))
    for item in restrictions:
        cautions.append(item['type']+' to verify: '+item['listing_excerpt'][:145])

    career_fit=evaluate_career_fit(job,resume_text)
    posting_requirements=extract_posting_requirements(job,resume_text)
    formal_requirements=extract_formal_minimums(job,resume_text)
    review_checks=posting_requirements['checks']+formal_requirements['checks']
    overlap=calibrate_cautions(specialties,career_fit['cautions'],review_checks)
    transfer=transfer_fit(
        qualification,job,alignment,overlap['domain_penalty'],
        credential_penalty,specialist_gap=overlap['specialist_gap'])

    for note in overlap['career_cautions']:
        cautions.append('Career fit to review: '+note['area']+
                        ' — '+note['reason'])
    for check in overlap['posting_checks']:
        if check['ranking_caution'] or check['type'] in ('Application eligibility','Residency / location'):
            cautions.append(check['type']+' to verify: '+check['area']+
                            ' — '+check['listing_excerpt'][:135])

    adjusted=max(0,transfer['index']-overlap['career_penalty']-
                 overlap['posting_penalty'])
    # Preserve the mandatory qualification caution and the original 90+
    # cap when a required degree or professional license lacks documentation.
    if formal_requirements['unverified_mandatory']:
        adjusted=min(adjusted,89)
    return {'index':adjusted,'role_alignment':alignment,
            'cautions':cautions,'specialties':overlap['specialties'],
            'career_fit_cautions':overlap['career_cautions'],
            'career_fit_penalty':overlap['career_penalty'],
            'posting_requirement_checks':overlap['posting_checks'],
            'posting_requirement_penalty':overlap['posting_penalty'],
            'ranking_overlap_relief':overlap['overlap_relief'],
            'ranking_overlap_note':overlap['adjustment_note'],
            'application_restricted':posting_requirements['application_restricted'],
            'transferable_strengths':transfer['transferable_strengths'],
            'duty_coverage':transfer['duty_coverage'],
            'confidence':('Limited details; inspect the employer posting' if
                          len(str(job.get('description') or ''))<450 else
                          'Based on available public job text; requirements may be incomplete')}
