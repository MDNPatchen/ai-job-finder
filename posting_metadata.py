"""Metadata that must not be guessed from a city name or a recruiting firm."""
import re


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
    if name in RECRUITER_NAMES:
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
