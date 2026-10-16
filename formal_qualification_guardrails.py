"""Conservative, explainable checks of mandatory education and licenses.

Read employer qualifications; never infer educational credentials from a job
title, salary, employer, or the candidate's career length. Degree equivalencies
and preferred degrees remain review items without strict ranking penalties.
Missing text in a résumé is NOT evidence that a person cannot qualify.
"""
import re
from posting_requirements import _clean, _qualification_scope

_DEGREE=re.compile(
    r"\b(?:(?:master|bachelor|associate|doctor)(?:[’']s)?\s+degree|"
    r"master\s+of\s+(?:business|science|arts|public|health)|"
    r"bachelor\s+of\s+(?:science|arts|business)|"
    r"(?:MBA|MHA|MPH|MPA)\s+(?:degree|qualification))\b",re.I)
_LEVELS=(
    ('doctorate',re.compile(r"\b(?:doctor(?:al|ate|[’']s)?\s+degree|Ph\.?D\.?)\b",re.I),28),
    ('master',re.compile(
        r"\b(?:master(?:[’']s)?\s+degree|master\s+of\s+(?:business|science|arts|public|health)|"
        r"(?:MBA|MHA|MPH|MPA)\s+(?:degree|qualification))\b",re.I),20),
    ('bachelor',re.compile(
        r"\b(?:bachelor(?:[’']s)?\s+degree|bachelor\s+of\s+(?:science|arts|business))\b",re.I),13),
    ('associate',re.compile(r"\bassociate(?:[’']s)?\s+degree\b",re.I),9),
)
_TECHNICAL_FIELD=re.compile(
    r"\b(?:architecture|architectural|engineering|construction engineering|"
    r"nursing|medicine|clinical science|laboratory science|"
    r"licensed clinical|social work|pharmacy)\b",re.I)
_BUSINESS_FIELD=re.compile(
    r"\b(?:business|administration|management|operations|"
    r"finance|accounting|marketing|public administration|health administration)\b",re.I)
_QUAL_CONTEXT=re.compile(
    r"\b(?:qualifications?|minimums?|requirements?|required|must|"
    r"education|experience|degree|credential|licen[sc]e|registration)\b",re.I)
_PREFERRED=re.compile(
    r"\b(?:preferred|a plus|desirable|nice to have|ideal|optional)\b",re.I)
_ALTERNATIVE=re.compile(
    r"\b(?:or\s+(?:equivalent|comparable)|equivalent\s+"
    r"(?:combination|experience|education)|"
    r"experience\s+(?:may|can)\s+(?:be\s+)?substitut(?:e|ed)|"
    r"substitution\s*:?|in lieu of)\b",re.I)
_LICENSE=re.compile(
    r"\b(?:licensed\s+(?:professional\s+)?(?:architect|engineer|physician|"
    r"nurse|attorney)|(?:architect(?:ural)?|engineering|"
    r"professional engineer|CPA|RN)\s+(?:license|licence|registration)|"
    r"registered\s+(?:architect|professional engineer)|"
    r"(?:PE|RA)\s+licen[sc]e)\b",re.I)


def _line(text,start,end):
    """Extract one item, rather than letting a later preferred degree leak in."""
    before=text.rfind('\n',0,start)
    after=text.find('\n',end)
    if after<0:
        after=len(text)
    # Avoid unrelated requirements in long flattened RSS paragraphs.
    piece=text[before+1:after]
    if len(piece)>550:
        lo=max(before+1,start-200)
        hi=min(after,end+230)
        piece=text[lo:hi]
    return piece.strip()


def _degree_status(line, degree_match, section):
    """Return preferred, equivalent, required, or mere mention."""
    local=line[degree_match.start():]
    # Do not let "Master's preferred" neutralize "Bachelor's required".
    following=_DEGREE.search(local[degree_match.end()-degree_match.start():])
    if following:
        local=local[:degree_match.end()-degree_match.start()+following.start()]
    ahead=local[:115]
    leading=line[max(0,degree_match.start()-90):degree_match.start()]
    if _PREFERRED.search(ahead) or (
        re.search(r"\bpreferred\b",leading,re.I) and
        not re.search(r"\brequired\b",ahead,re.I)):
        return 'Preferred / mentioned'
    if _ALTERNATIVE.search(line) or _ALTERNATIVE.search(
            line[max(0,degree_match.start()-75):degree_match.end()+180]):
        return 'Alternative route or equivalent experience — verify'
    if re.search(r"\b(?:required|mandatory|must|minimum)\b",ahead,re.I):
        return 'Required / minimum — verify exact wording'
    if (re.search(r"\b(?:qualifications?|education|requirements?|"
                  r"what you.ll need|what you need|what you.ll bring)\b",section,re.I)
            or re.search(r"\b(?:requirements?|qualifications?|education"
                         r"(?:\s+and/or\s+experience)?)\s*:?\s*$",leading,re.I)):
        return 'Required / minimum — qualifications section'
    return 'Mentioned — verify status'


def _degree_resume_evidence(resume, level, required_line):
    idx=next((i for i,(name,_,_) in enumerate(_LEVELS) if name==level),99)
    level_found=any(i<=idx and bool(pattern.search(resume))
                    for i,(_,pattern,_) in enumerate(_LEVELS))
    if not level_found:
        return False,'Required degree level not established by résumé; independently verify.'
    if _TECHNICAL_FIELD.search(required_line):
        # Technical education must be apparent in a declared degree
        # context, not just generic engineering oversight in work history.
        relevant=bool(re.search(
            r"(?:bachelor|master|doctor|degree).{0,100}"
            r"(?:architecture|architectural|engineering|nursing|medicine|"
            r"pharmacy|clinical science|laboratory science)|"
            r"(?:architecture|architectural|engineering|nursing|medicine|"
            r"pharmacy|clinical science|laboratory science).{0,75}"
            r"(?:degree|bachelor|master|doctor)",resume,re.I))
        if not relevant:
            return False,'Degree level mentioned, but required technical field not established by résumé.'
    elif _BUSINESS_FIELD.search(required_line):
        # A business/management degree can often span administration and
        # related fields, but an unrelated bachelor's should not suffice.
        if not re.search(r"(?:degree|bachelor|master).{0,95}"
                         r"(?:business|administration|management|finance|"
                         r"accounting|marketing)|"
                         r"(?:business|administration|management|finance|"
                         r"accounting|marketing).{0,80}(?:degree|bachelor|master)",
                         resume,re.I):
            return False,'Degree level mentioned, but stated business/administrative field needs verification.'
    return True,'Related degree level and field mentioned; verify award and equivalency.'


def extract_formal_minimums(job, resume=''):
    desc=_clean(job.get('description'))
    resume=_clean(resume)
    out=[]
    seen=set()
    for level,pattern,base_penalty in _LEVELS:
        for match in list(pattern.finditer(desc))[:12]:
            # Skip mismatched fragments, references in unrelated narrative,
            # and benefits/education-assistance descriptions.
            line=_line(desc,match.start(),match.end())
            local=pattern.search(line)
            if not local:
                continue
            section=_qualification_scope(desc,match.start())
            if re.search(r"\b(?:benefits|perks|what we offer|"
                         r"tuition reimbursement|professional development)\b",
                         section,re.I):
                continue
            if re.search(r"\b(?:tuition reimbursement|education assistance|"
                         r"student loan forgiveness)\b",line,re.I):
                continue
            if not (_QUAL_CONTEXT.search(line) or
                    re.search(r"\b(?:qualifications?|education|requirements?)\b",section,re.I)):
                continue
            priority=_degree_status(line,local,section)
            # Scope only a degree-specific excerpt to avoid nearby preferred
            # degrees changing the required master's or bachelor's status.
            key=(level,priority)
            if key in seen:
                continue
            seen.add(key)
            verified,status=_degree_resume_evidence(resume,level,line)
            mandatory=priority.startswith('Required')
            score=(base_penalty if mandatory and not verified else 0)
            if _TECHNICAL_FIELD.search(line) and mandatory and not verified:
                score=max(score,22)
            out.append({
                'area':level.capitalize()+' degree'+
                       (' in technical/professional field' if _TECHNICAL_FIELD.search(line) else ''),
                'type':'Education / professional credential',
                'priority':priority,
                'listing_excerpt':re.sub(r'\s+',' ',line)[:280],
                'resume_status':status,
                'ranking_caution':score
            })
            break

    # Require explicit licensure, not simply a "registered professionals" duty.
    for match in list(_LICENSE.finditer(desc))[:12]:
        line=_line(desc,match.start(),match.end())
        section=_qualification_scope(desc,match.start())
        if not (_QUAL_CONTEXT.search(line) or
                re.search(r'\b(?:qualifications?|requirements?|education)\b',section,re.I)):
            continue
        local=_LICENSE.search(line)
        if not local:
            continue
        tail=line[local.start():local.end()+120]
        if _PREFERRED.search(tail):
            priority='Preferred / mentioned'
        elif re.search(r'\b(?:required|must|mandatory|active|current)\b',
                       line,re.I) or re.search(
                           r'\b(?:qualifications?|requirements?)\b',section,re.I):
            priority='Required / minimum — verify exact wording'
        else:
            priority='Mentioned — verify status'
        # Never treat "supervise licensed architects" as personal licensing.
        if re.search(r'\b(?:supervise|manage|work with|coordinate with|'
                     r'lead teams of)\s+(?:licensed|registered)\b',line,re.I):
            continue
        related=bool(re.search(r'\b(?:architectural license|architect licen[sc]e|'
                               r'licensed architect|PE license|licensed professional '
                               r'engineer|registered architect)\b',resume,re.I))
        score=22 if priority.startswith('Required') and not related else 0
        out.append({
            'area':'Professional license / registration',
            'type':'Education / professional credential',
            'priority':priority,'listing_excerpt':re.sub(r'\s+',' ',line)[:280],
            'resume_status':('Possible professional credential mentioned in résumé; verify current standing.'
                             if related else
                             'Active professional licensure not established by résumé.'),
            'ranking_caution':score
        })
        break
    return {'checks':out,
            'ranking_caution':min(38,sum(x['ranking_caution'] for x in out)),
            'unverified_mandatory':any(x['ranking_caution']>0 for x in out)}
