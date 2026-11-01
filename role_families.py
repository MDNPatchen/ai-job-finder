"""Role families where a publisher / general manager's experience transfers.

Publisher openings are scarce, so the finder looks across adjacent families.
Each family lists the job titles that belong to it and the skill areas that
decide success there. A person's readiness for a family is the weighted share
of those skill areas they can show: proven or described in the resume counts
fully, confirmed in the profile counts partly, and missing areas are gaps.
No AI; every number traces back to a resume line or a profile answer.
"""
import re

FAMILIES = (
    {'key': 'media', 'label': 'Media & publishing leadership',
     'titles': r'\b(?:group )?publisher\b|\b(?:station|media|broadcast) (?:manager|director)\b|\b(?:director|vp|vice president) of (?:audience|circulation|news operations)\b|\beditor[- ]in[- ]chief\b',
     'skills': {'Financial & P&L leadership': 3, 'Revenue growth & transformation': 3, 'Advertising & sales leadership': 2,
                'Editorial & cross-functional leadership': 2, 'Audience & marketing development': 2, 'Digital transformation': 2},
     'why': 'Same industry and scope as your current role.'},
    {'key': 'operations', 'label': 'General management & operations',
     'titles': r'\b(?:general manager|chief operating officer|coo|chief administrative officer|managing director)\b|\b(?:regional|district|area) (?:operations )?(?:director|manager|vice president|vp)\b|\b(?:director|vp|vice president|head) of (?:operations|business operations|administration)\b|\boperations (?:director|manager|vice president|vp)\b|\b(?:business|office) manager\b|\b(?:production|plant|print(?:ing)?|pressroom) (?:director|manager|operations manager)\b',
     'skills': {'Operations leadership': 3, 'Financial & P&L leadership': 3, 'Multi-site business leadership': 2,
                'Talent & organizational change': 2, 'Negotiation & vendor management': 2, 'Strategic planning & execution': 1},
     'why': 'Running budgets, multiple sites, staff and vendors is the core of general management.'},
    {'key': 'communications', 'label': 'Communications & public affairs',
     'titles': r'\b(?:communications?|public (?:relations|affairs|information)|media relations|community relations|external (?:relations|affairs)|corporate communications|marketing communications)\b.{0,20}\b(?:director|manager|officer|lead|vice president|vp|head|specialist)\b|\b(?:director|vp|vice president|head|chief) of (?:communications|public (?:relations|affairs|information)|media relations|community relations|external (?:affairs|relations))\b|\bpublic information officer\b|\bpio\b|\bspokes(?:person|man|woman)\b',
     'skills': {'Communications & public relations': 3, 'Community partnerships': 2, 'Audience & marketing development': 2,
                'Digital transformation': 1, 'Strategic planning & execution': 1},
     'why': 'You are the spokesperson and run multi-channel communications plans.'},
    {'key': 'marketing', 'label': 'Marketing, audience & membership',
     'titles': r'\b(?:marketing|brand|audience|membership|member services|customer experience|engagement|growth) (?:director|manager|vice president|vp|lead|head)\b|\b(?:director|vp|vice president|head|chief) of (?:marketing|brand|audience|membership|engagement|growth)\b|\bchief marketing officer\b|\bcmo\b',
     'skills': {'Audience & marketing development': 3, 'Digital transformation': 2, 'Reporting & data analysis': 2,
                'Revenue growth & transformation': 1, 'Communications & public relations': 1},
     'why': 'Audience growth, circulation and digital engagement are marketing work.'},
    {'key': 'sales', 'label': 'Sales, advertising & partnerships',
     'titles': r'\b(?:sales|advertising|ad sales|business development|revenue|partnerships?|sponsorships?|account) (?:director|manager|vice president|vp|lead|head)\b|\b(?:director|vp|vice president|head|chief) of (?:sales|advertising|business development|revenue|partnerships|sponsorships)\b|\bchief revenue officer\b|\bcro\b',
     'skills': {'Advertising & sales leadership': 3, 'Revenue growth & transformation': 3, 'Negotiation & vendor management': 2,
                'Community partnerships': 2, 'Talent & organizational change': 1},
     'why': 'Publishers own advertising revenue and local business relationships.'},
    {'key': 'community', 'label': 'Community, tourism & economic development',
     'titles': r'\b(?:chamber of commerce|chamber|convention (?:&|and) visitors? bureau|cvb|visitors? bureau|tourism|destination|economic development|downtown|main street|business improvement district|development corporation)\b.{0,40}\b(?:president|ceo|director|executive|manager)\b|\b(?:president|ceo|director|executive director|manager)\s*(?:of|,|-|–)?\s*(?:the )?(?:[\w&.]+ ){0,3}(?:chamber|tourism|economic development|visitors? bureau|downtown|main street|visit [a-z]+)\b',
     'skills': {'Community partnerships': 3, 'Communications & public relations': 2, 'Fundraising & development': 2,
                'Revenue growth & transformation': 1, 'Strategic planning & execution': 2, 'Audience & marketing development': 1},
     'why': 'A local publisher already knows the business community, civic leaders and how to promote a region.'},
    {'key': 'nonprofit', 'label': 'Nonprofit leadership & fundraising',
     'titles': r'\bexecutive director\b|\b(?:development|advancement|philanthropy|fundraising|major gifts|foundation) (?:director|manager|officer|vice president|vp)\b|\b(?:director|vp|vice president|chief) of (?:development|advancement|philanthropy|programs?)\b|\b(?:nonprofit|foundation|association|united way|ymca|boys (?:&|and) girls club) (?:president|ceo|director|executive)\b|\bpresident (?:&|and) ceo\b',
     'skills': {'Fundraising & development': 3, 'Community partnerships': 3, 'Financial & P&L leadership': 2,
                'Strategic planning & execution': 2, 'Communications & public relations': 1, 'Talent & organizational change': 1},
     'why': 'Board work, donor relationships and budget oversight carry straight into nonprofit leadership.'},
    {'key': 'government', 'label': 'Public administration',
     'titles': r'\b(?:city|county|town|village|borough) (?:administrator|manager)\b|\b(?:deputy|assistant) (?:city|county|town) (?:administrator|manager)\b|\b(?:administrative services|support services) (?:director|manager)\b|\bchief of staff\b|\bcounty executive\b|\b(?:director|deputy director) of (?:administration|administrative services|community development)\b',
     'skills': {'Financial & P&L leadership': 3, 'Operations leadership': 2, 'Community partnerships': 2,
                'Communications & public relations': 2, 'Talent & organizational change': 2, 'Government administration': 2},
     'why': 'Budgets, staff, public communication and community relationships transfer; public-sector rules are the gap to close.'},
    {'key': 'distribution', 'label': 'Distribution & logistics',
     'titles': r'\b(?:distribution|logistics|fulfillment|fleet|transportation|warehouse|supply chain|delivery) (?:director|manager|vice president|vp|lead|head)\b|\b(?:director|vp|vice president|head) of (?:distribution|logistics|fulfillment|supply chain|transportation)\b',
     'skills': {'Distribution & logistics': 3, 'Operations leadership': 2, 'Negotiation & vendor management': 2,
                'Talent & organizational change': 1, 'Reporting & data analysis': 1},
     'why': 'Circulation is a daily distribution and delivery network.'},
)
_COMPILED = tuple((f, re.compile(f['titles'], re.I)) for f in FAMILIES)
BY_KEY = {f['key']: f for f in FAMILIES}
LABELS = tuple(f['label'] for f in FAMILIES)

# Credit for each kind of support, matching the resume interpretation grades.
# Unquantified claims are discounted: employers weigh numbers heavily.
CREDIT = {'Proven': 1.0, 'Described': 0.7, 'Volunteer': 0.5, 'Summary': 0.35, 'Confirmed': 0.5}


def family_for_title(title):
    """First family whose title pattern matches, or None."""
    text = str(title or '')
    for family, pattern in _COMPILED:
        if pattern.search(text):
            return family
    return None


def readiness(family, grades):
    """Weighted share of a family's key skills the person can show.

    grades: {area: grade} from career_profile.interpret_resume.
    Returns score 0-100, strengths (with grade) and gaps, strongest first.
    """
    total = sum(family['skills'].values())
    earned = 0.0
    strengths, gaps = [], []
    for area, weight in sorted(family['skills'].items(), key=lambda kv: -kv[1]):
        grade = grades.get(area, 'Not shown')
        credit = CREDIT.get(grade, 0.0)
        earned += weight * credit
        (strengths if credit else gaps).append({'area': area, 'grade': grade, 'weight': weight})
    return {'key': family['key'], 'label': family['label'], 'why': family['why'],
            'score': round(100 * earned / total) if total else 0,
            'strengths': strengths, 'gaps': gaps}


def rank_families(grades):
    """All families, best transfer first."""
    return sorted((readiness(f, grades) for f in FAMILIES), key=lambda r: (-r['score'], r['label']))


def explain_job(job_title, qualification, grades=None):
    """One-line 'why this transfers' for a job card, from its own match data."""
    family = family_for_title(job_title)
    matched = [x['area'] for x in (qualification or {}).get('resume_matches') or []
               if x.get('match_origin') != 'Job title only']
    confirmed = [x['area'] for x in (qualification or {}).get('confirmed_only') or []]
    gaps = [x['area'] for x in (qualification or {}).get('not_documented') or []]
    if family and grades:
        # Put the family's decisive skills first.
        order = {a: -w for a, w in family['skills'].items()}
        matched.sort(key=lambda a: order.get(a, 0))
        gaps.sort(key=lambda a: order.get(a, 0))
    return {'family': family['label'] if family else '',
            'transfers': matched[:3], 'confirmed': confirmed[:2], 'gaps': gaps[:3]}
