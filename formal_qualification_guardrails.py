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
    r"construction management|construction science|preconstruction|"
    r"nursing|medicine|clinical science|laboratory science|"
    r"licensed clinical|social work|pharmacy)\b",re.I)
_BUSINESS_FIELD=re.compile(
    r"\b(?:business(?: administration| management)?|"
    r"operations management|health(?:care| care) administration|"
    r"public administration|finance|accounting|marketing)\b",re.I)
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
    """Read the entire applicant degree clause, not just 115 characters."""
    local=line[degree_match.start():]
    subsequent=_DEGREE.search(local[degree_match.end()-degree_match.start():])
    if subsequent:
        local=local[:degree_match.end()-degree_match.start()+subsequent.start()]
    # Do not borrow preferred language from separate bullets or degrees.
    local=re.split(r'(?=\s+[•●]\s)|\n',local,maxsplit=1)[0][:450]
    preceding=line[max(0,degree_match.start()-95):degree_match.start()]
    # A preceding explicit "Requires a Bachelor's degree" must carry
    # mandatory force even though the degree itself is not followed by
    # the word "required". Older code only searched after "Bachelor's".
    explicit_lead=bool(re.search(
        r'\b(?:requires?|requiring|must\s+(?:have|hold|possess)|'
        r'mandates?|minimum\s+(?:of\s+)?)\s+(?:an?\s+)?
    if re.search(r'\b(?:education\s+and/or\s+experience|'
                 r'education(?:al)?\s+requirements?)\s*:\s*[•*\-]?\s*$',
                 preceding,re.I):
        return 'Required / minimum — employer education section'
    if re.search(r'\b(?:required|mandatory|must|minimum)\b',local,re.I):
        return 'Required / minimum — verify exact wording'
    if (re.search(r'\b(?:qualifications?|education|requirements?|'
                  r'what you.ll need|what you need|what you.ll bring)\b',section,re.I)
            or re.search(r'\b(?:requirements?|qualifications?|education'
                         r'(?:\s+and/or\s+experience)?)\s*:?\s*$',
                         preceding,re.I)):
        return 'Required / minimum — qualifications section'
    return 'Mentioned — verify status'


def _degree_resume_evidence(resume, level, required_line):
    """Verify the exact eligible discipline, not generic 'management'.

    Construction Management is a professional field, not equivalent to
    Business Management merely because both include the word management.
    Accept an explicit Business/Operations degree only if the employer
    actually names it as an alternative discipline.
    """
    idx=next((i for i,(name,_,_) in enumerate(_LEVELS) if name==level),99)
    level_found=any(i<=idx and bool(pattern.search(resume))
                    for i,(_,pattern,_) in enumerate(_LEVELS))
    if not level_found:
        return False,'Required degree level not established by résumé; independently verify.'

    business_evidence=bool(re.search(
        r'(?:bachelor|master|doctor|degree).{0,100}'
        r'(?:business|public administration|health(?:care| care) administration|'
        r'operations management|finance|accounting|marketing)|'
        r'(?:business|public administration|health(?:care| care) administration|'
        r'operations management|finance|accounting|marketing).{0,85}'
        r'(?:degree|bachelor|master|doctor)',resume,re.I))
    business_offered=bool(_BUSINESS_FIELD.search(required_line))
    # A degree in construction management never matches a business degree;
    # generic "management" and "related field" are insufficient alternatives.
    if business_offered and business_evidence:
        return True,'Employer explicitly names a related business discipline; verify degree level and acceptance.'

    if _TECHNICAL_FIELD.search(required_line):
        technical_evidence=bool(re.search(
            r'(?:bachelor|master|doctor|degree).{0,110}'
            r'(?:architecture|architectural|engineering|construction management|'
            r'construction science|nursing|medicine|pharmacy|clinical science|'
            r'laboratory science)|'
            r'(?:architecture|architectural|engineering|construction management|'
            r'construction science|nursing|medicine|pharmacy|clinical science|'
            r'laboratory science).{0,90}(?:degree|bachelor|master|doctor)',
            resume,re.I))
        if not technical_evidence:
            return False,('Required construction, engineering or other technical '
                          'degree discipline is not documented; general business '
                          'management does not establish equivalence.')
        return True,'Relevant technical degree appears in résumé; verify award and approved discipline.'

    if business_offered:
        if not business_evidence:
            return False,'Degree level mentioned, but stated business/administrative discipline needs verification.'
        return True,'Related business degree is mentioned; verify award and discipline.'

    return True,'Degree level is mentioned; confirm employer discipline requirements.'



_ALTERNATIVE_DEGREE_CONNECTOR=re.compile(
    r'\b(?:or|alternatively|either)\s*[,;:]?\s*(?:an?\s+)?$',re.I)


def _reconcile_degree_pathways(desc, degree_hits):
    """Count one required education pathway, not every offered alternative."""
    group=[]
    groups=[]
    for hit in sorted(degree_hits,key=lambda x:x[0]):
        if group:
            prior=group[-1]
            between=desc[prior[1]:hit[0]]
            linked=(prior[2]!=hit[2] and len(between)<=950
                    and _ALTERNATIVE_DEGREE_CONNECTOR.search(between[-130:])
                    and prior[3]['priority'].startswith('Required')
                    and hit[3]['priority'].startswith('Required'))
            if not linked:
                if len(group)>1:
                    groups.append(group)
                group=[]
        group.append(hit)
    if len(group)>1:
        groups.append(group)

    for group in groups:
        penalties=[int(item['ranking_caution']) for *_,item in group]
        cheapest=min(penalties)
        winner=penalties.index(cheapest) if cheapest>0 else -1
        paths=' / '.join(level.capitalize()+"'s" for _,_,level,_ in group)
        for ix,(_,_,level,item) in enumerate(group):
            original=item['ranking_caution']
            if ix!=winner:
                item['ranking_caution']=0
                if original:
                    item['covered_by_alternative_degree_pathway']=True
            item['alternative_degree_pathways']=paths
            item['priority']+=' — alternative degree route (not cumulative)'
            item['resume_status']+=(
                ' These are alternate degree routes, not cumulative education '
                'requirements; verify the experience minimum for each route.'
            )


def extract_formal_minimums(job, resume=''):
    desc=_clean(job.get('description'))
    resume=_clean(resume)
    out=[]
    seen=set()
    degree_hits=[]
    for level,pattern,base_penalty in _LEVELS:
        for match in list(pattern.finditer(desc))[:12]:
            # Skip mismatched fragments, references in unrelated narrative,
            # and benefits/education-assistance descriptions.
            line=_line(desc,match.start(),match.end())
            local=pattern.search(line)
            if not local:
                continue
            section=_qualification_scope(desc,match.start())
            if not section:
                # Some ATS feeds place EDUCATION and/or EXPERIENCE directly
                # before the required degree in the same paragraph.
                prefix=desc[max(0,match.start()-200):match.start()]
                heading_re=(r'\b(?:education\s+and/or\s+experience|'
                            r'education(?:al)?\s+requirements?|'
                            r'minimum\s+qualifications?)\s*:\s*'
                            r'(?:[•●*\-]\s*)?$')
                if re.search(heading_re,prefix,re.I):
                    section='education'
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
            degree_hits.append((match.start(),match.end(),level,out[-1]))
            break

    _reconcile_degree_pathways(desc,degree_hits)

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
,preceding,re.I))
    if re.search(r'\b(?:preferred|desirable|nice to have|optional|a plus)\b',
                 local,re.I):
        return 'Preferred / mentioned'
    if _ALTERNATIVE.search(local) or _ALTERNATIVE.search(
            line[max(0,degree_match.start()-75):degree_match.end()+180]):
        return 'Alternative route or equivalent experience — verify'
    if explicit_lead:
        return 'Required / minimum — explicit degree requirement'
    if (re.search(r'\b(?:preferred|desirable|nice to have)\b',preceding,re.I)
            and not re.search(r'\b(?:required|mandatory|must)\b',local,re.I)):
        return 'Preferred / mentioned'
    if re.search(r'\b(?:education\s+and/or\s+experience|'
                 r'education(?:al)?\s+requirements?)\s*:\s*[•*\-]?\s*$',
                 preceding,re.I):
        return 'Required / minimum — employer education section'
    if re.search(r'\b(?:required|mandatory|must|minimum)\b',local,re.I):
        return 'Required / minimum — verify exact wording'
    if (re.search(r'\b(?:qualifications?|education|requirements?|'
                  r'what you.ll need|what you need|what you.ll bring)\b',section,re.I)
            or re.search(r'\b(?:requirements?|qualifications?|education'
                         r'(?:\s+and/or\s+experience)?)\s*:?\s*$',
                         preceding,re.I)):
        return 'Required / minimum — qualifications section'
    return 'Mentioned — verify status'


def _degree_resume_evidence(resume, level, required_line):
    """Verify the exact eligible discipline, not generic 'management'.

    Construction Management is a professional field, not equivalent to
    Business Management merely because both include the word management.
    Accept an explicit Business/Operations degree only if the employer
    actually names it as an alternative discipline.
    """
    idx=next((i for i,(name,_,_) in enumerate(_LEVELS) if name==level),99)
    level_found=any(i<=idx and bool(pattern.search(resume))
                    for i,(_,pattern,_) in enumerate(_LEVELS))
    if not level_found:
        return False,'Required degree level not established by résumé; independently verify.'

    business_evidence=bool(re.search(
        r'(?:bachelor|master|doctor|degree).{0,100}'
        r'(?:business|public administration|health(?:care| care) administration|'
        r'operations management|finance|accounting|marketing)|'
        r'(?:business|public administration|health(?:care| care) administration|'
        r'operations management|finance|accounting|marketing).{0,85}'
        r'(?:degree|bachelor|master|doctor)',resume,re.I))
    business_offered=bool(_BUSINESS_FIELD.search(required_line))
    # A degree in construction management never matches a business degree;
    # generic "management" and "related field" are insufficient alternatives.
    if business_offered and business_evidence:
        return True,'Employer explicitly names a related business discipline; verify degree level and acceptance.'

    if _TECHNICAL_FIELD.search(required_line):
        technical_evidence=bool(re.search(
            r'(?:bachelor|master|doctor|degree).{0,110}'
            r'(?:architecture|architectural|engineering|construction management|'
            r'construction science|nursing|medicine|pharmacy|clinical science|'
            r'laboratory science)|'
            r'(?:architecture|architectural|engineering|construction management|'
            r'construction science|nursing|medicine|pharmacy|clinical science|'
            r'laboratory science).{0,90}(?:degree|bachelor|master|doctor)',
            resume,re.I))
        if not technical_evidence:
            return False,('Required construction, engineering or other technical '
                          'degree discipline is not documented; general business '
                          'management does not establish equivalence.')
        return True,'Relevant technical degree appears in résumé; verify award and approved discipline.'

    if business_offered:
        if not business_evidence:
            return False,'Degree level mentioned, but stated business/administrative discipline needs verification.'
        return True,'Related business degree is mentioned; verify award and discipline.'

    return True,'Degree level is mentioned; confirm employer discipline requirements.'



_ALTERNATIVE_DEGREE_CONNECTOR=re.compile(
    r'\b(?:or|alternatively|either)\s*[,;:]?\s*(?:an?\s+)?$',re.I)


def _reconcile_degree_pathways(desc, degree_hits):
    """Count one required education pathway, not every offered alternative."""
    group=[]
    groups=[]
    for hit in sorted(degree_hits,key=lambda x:x[0]):
        if group:
            prior=group[-1]
            between=desc[prior[1]:hit[0]]
            linked=(prior[2]!=hit[2] and len(between)<=950
                    and _ALTERNATIVE_DEGREE_CONNECTOR.search(between[-130:])
                    and prior[3]['priority'].startswith('Required')
                    and hit[3]['priority'].startswith('Required'))
            if not linked:
                if len(group)>1:
                    groups.append(group)
                group=[]
        group.append(hit)
    if len(group)>1:
        groups.append(group)

    for group in groups:
        penalties=[int(item['ranking_caution']) for *_,item in group]
        cheapest=min(penalties)
        winner=penalties.index(cheapest) if cheapest>0 else -1
        paths=' / '.join(level.capitalize()+"'s" for _,_,level,_ in group)
        for ix,(_,_,level,item) in enumerate(group):
            original=item['ranking_caution']
            if ix!=winner:
                item['ranking_caution']=0
                if original:
                    item['covered_by_alternative_degree_pathway']=True
            item['alternative_degree_pathways']=paths
            item['priority']+=' — alternative degree route (not cumulative)'
            item['resume_status']+=(
                ' These are alternate degree routes, not cumulative education '
                'requirements; verify the experience minimum for each route.'
            )


def extract_formal_minimums(job, resume=''):
    desc=_clean(job.get('description'))
    resume=_clean(resume)
    out=[]
    seen=set()
    degree_hits=[]
    for level,pattern,base_penalty in _LEVELS:
        for match in list(pattern.finditer(desc))[:12]:
            # Skip mismatched fragments, references in unrelated narrative,
            # and benefits/education-assistance descriptions.
            line=_line(desc,match.start(),match.end())
            local=pattern.search(line)
            if not local:
                continue
            section=_qualification_scope(desc,match.start())
            if not section:
                # Some ATS feeds place EDUCATION and/or EXPERIENCE directly
                # before the required degree in the same paragraph.
                prefix=desc[max(0,match.start()-200):match.start()]
                heading_re=(r'\b(?:education\s+and/or\s+experience|'
                            r'education(?:al)?\s+requirements?|'
                            r'minimum\s+qualifications?)\s*:\s*'
                            r'(?:[•●*\-]\s*)?$')
                if re.search(heading_re,prefix,re.I):
                    section='education'
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
            degree_hits.append((match.start(),match.end(),level,out[-1]))
            break

    _reconcile_degree_pathways(desc,degree_hits)

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
