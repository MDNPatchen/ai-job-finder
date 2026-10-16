"""Metadata that must not be guessed from a city name or a recruiting firm."""
import re
from employer_postings import is_recruiter_employer


def affirmative(value):
    """Parse provider booleans without treating the string 'false' as truthy."""
    return value is True or (isinstance(value, str) and
                             value.strip().casefold() in ('yes', 'true', '1'))


def declared_arrangement(value):
    """Use only an explicit provider label, not an implied office location."""
    label=str(value or '').strip().casefold().replace('_', '-')
    if label in ('hybrid','hybrid-work','partially-remote','partly remote'):
        return 'Hybrid'
    if label in ('onsite','on-site','on site','in-person','office-based',
                 'office', 'in-office'):
        return 'On-site'
    if label in ('remote','fully-remote','remote-only','work from home'):
        return 'Remote'
    return ''


def strict_onsite_requirement(description):
    """Full-time in-person requirement, not a hybrid office-day schedule."""
    text=re.sub(r'\s+',' ',str(description or ''))[:12500]
    if re.search(r'\bhybrid\s+(?:role|work|schedule|arrangement|model)\b',text,re.I):
        return False
    terms=(
        r'\b(?:this\s+)?(?:position|job|role)\s+(?:is\s+)?'
        r'(?:required|expected)\s+to\s+(?:work|report|be)\s+'
        r'(?:on[- ]site|onsite|in[- ]person|in\s+(?:the|our)\s+office)\b',
        r'\b(?:must|required to)\s+(?:work|report|be)\s+'
        r'(?:on[- ]site|onsite|in[- ]person|in\s+(?:the|our)\s+office)\b',
        r'\b(?:on[- ]site|in[- ]person)\s+(?:attendance|work)\s+'
        r'(?:is\s+)?(?:mandatory|required)\b',
        r'\b(?:fully|100%|entirely)\s+(?:on[- ]site|onsite|in[- ]person)\b',
        r'\b(?:five|5)\s+days?\s+(?:a|per)\s+week\s+'
        r'(?:on[- ]site|onsite|in[- ]person|in\s+(?:the|our)\s+office)\b',
    )
    return any(re.search(term,text,re.I) for term in terms)


def from_explicit_description(description):
    """Conservative job-specific arrangement text, not every occurrence of 'office'."""
    text=re.sub(r'\s+',' ',str(description or ''))[:12500]
    labels=(
        ('Hybrid',r'\b(?:work(?:place)? (?:arrangement|model|type)|'
                  r'location type)\s*:\s*hybrid\b|'
                  r'\b(?:hybrid|flexible)\s+(?:work|schedule|position|role|arrangement|model)\b|'
                  r'\b(?:role|position|job)\s+(?:is\s+)?hybrid\b'),
        ('On-site',r'\b(?:work(?:place)? (?:arrangement|model|type)|'
                   r'location type)\s*:\s*(?:on[- ]site|in[- ]office)\b|'
                   r'\b(?:on[- ]site|onsite|in[- ]person)\s+'
                   r'(?:position|work|role|attendance|required|schedule)\b|'
                   r'\b(?:role|position|job)\s+(?:is\s+)?(?:on[- ]site|onsite)\b|'
                   r'\b(?:must|required to)\s+(?:work|report|be)\s+'
                   r'(?:on[- ]site|in[- ]person|in (?:the|our) office)\b'),
        ('Remote',r'\b(?:work(?:place)? (?:arrangement|model|type)|'
                  r'location type)\s*:\s*(?:fully\s+)?remote\b|'
                  r'\b(?:fully|100%|entirely|completely)\s+remote\b|'
                  r'\bremote[- ]only\b|'
                  r'\b(?:role|position|job)\s+is\s+(?:fully\s+)?remote\b|'
                  r'\bwork from anywhere\b'),
    )
    candidates=[]
    for style,pattern in labels:
        for match in re.finditer(pattern,text,re.I):
            before=text[max(0,match.start()-25):match.start()]
            if re.search(r'\b(?:not|isn.t|no|without)\s+(?:a\s+)?$',before,re.I):
                continue
            candidates.append(style)
    unique=set(candidates)
    # Conflicting labels are ambiguous and should not be silently resolved.
    return candidates[0] if len(unique)==1 else ''


RECRUITER_NAMES=frozenset((
    'keller executive search',
    'hoa talent',
))


def employer_identity_kind(company):
    """Poster/recruiter is not necessarily the underlying hiring client."""
    name=re.sub(r'\s+',' ',str(company or '')).strip().casefold()
    if name in RECRUITER_NAMES or is_recruiter_employer(name):
        return 'Recruiting intermediary named; underlying hiring company unverified'
    return 'Company named by source; hiring identity not independently verified'


def greenhouse_workplace_label(metadata):
    """Return an ATS-supplied work label only when its field name says so."""
    if not isinstance(metadata,list):
        return ''
    for item in metadata:
        if not isinstance(item,dict):
            continue
        name=str(item.get('name') or '').strip().casefold()
        if name not in ('workplace type','work arrangement','work model',
                        'work location type','working model','work mode'):
            continue
        raw=item.get('value')
        for value in raw if isinstance(raw,list) else [raw]:
            style=declared_arrangement(value)
            if style:
                return style
    return ''


# Records from public feeds may have been cached before the current parsing
# rules were deployed. Normalize *both* the work style and its provenance
# when those records are ranked/exported; avoid mutating provider cache data.
NO_WORKPLACE_EVIDENCE = 'No explicit workplace label in public posting'
WORKPLACE_SOURCE_UNVERIFIED = (
    'Work arrangement reported; original evidence not retained — verify employer posting'
)


def reconcile_workplace_record(job):
    """Preserve recognized work styles, but never invent their provenance.

    If an older cache entry says "Not specified" while claiming evidence was
    found, it has no established work-arrangement source. If a recognizable
    On-site/Hybrid/Remote label has no matching evidence, keep the label but
    explicitly mark its source unverified rather than fabricating an ATS field.
    """
    out=dict(job)
    style=declared_arrangement(out.get('work_style'))
    if not style:
        style='Remote' if affirmative(out.get('remote')) else 'Not specified'
    original_source=str(out.get('arrangement_source') or '').strip()

    if style=='Not specified':
        source=NO_WORKPLACE_EVIDENCE
    elif original_source=='Employer ATS workplace label':
        source=original_source
    elif original_source=='Provider remote flag' and style=='Remote' and affirmative(out.get('remote')):
        source=original_source
    else:
        # Only infer from plainly labeled description/location text. A city
        # itself is not evidence of an on-site requirement.
        description=from_explicit_description(out.get('description'))
        location=str(out.get('location') or '')
        if re.search(r'\bhybrid\b',location,re.I):
            location_style='Hybrid'
        elif re.search(r'\b(?:fully\s+)?remote\b',location,re.I):
            location_style='Remote'
        elif re.search(r'\b(?:on[- ]site|onsite|in[- ]person|office[- ]based)\b',
                       location,re.I):
            location_style='On-site'
        else:
            location_style=''
        if style in (description,location_style):
            source='Posting location or description text'
        elif original_source=='Provider remote flag' and style=='Remote':
            source='Provider remote flag'
        else:
            source=WORKPLACE_SOURCE_UNVERIFIED

    out['work_style']=style
    out['remote']=(style=='Remote')
    out['arrangement_source']=source
    return out
