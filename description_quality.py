"""Content quality is distinct from the origin of a posting's text."""
import re

DETAILED_SOURCES=frozenset(('Employer posting details as supplied by provider',
                           'Official full public job bulletin'))


def assess_description(job):
    text=re.sub(r'\s+',' ',str(job.get('description') or '')).strip()
    source=str(job.get('description_source') or '')
    partial='rss summary' in source.lower() or 'rss text' in source.lower()
    requirements=bool(re.search(r'\b(?:minimum|required|preferred) qualifications?\b|'
                               r'\brequirements\b|\bqualifications\b',text,re.I))
    duties=bool(re.search(r'\b(?:responsibilit\w*|duties|manage|lead|oversee|coordinate|'
                         r'develop|support|supervise|deliver|responsible)\b',text,re.I))
    truncated=bool(job.get('description_truncated'))
    detailed=(len(text)>=450 and duties and source in DETAILED_SOURCES and not partial and not truncated)
    label=('Missing description' if not text else 'Truncated text — review original' if truncated
           else 'Summary / unverified RSS text' if partial else
           'Detailed text with qualification section' if detailed and requirements else
           'Detailed duties; qualification section not identified' if detailed else
           'Limited or unverified description')
    return {'label':label,'detailed':detailed,'requirements_section':requirements,
            'characters':len(text),'truncated':truncated}
