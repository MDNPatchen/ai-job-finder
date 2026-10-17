"""Verified manual routes for unavailable automated feeds; never count as recovered."""
ROUTES={
    'Bold Business':('https://insights.boldbusiness.com/careers/',
        'Configured Greenhouse board returned 404. The official career page links to a different hiring service; automated coverage remains unavailable.'),
    'Duval County Public Schools':('https://jobs.duvalschools.org/',
        'The configured RSS endpoint reports an invalid agency or disabled feed. Review the district’s current career site.'),
    'Ventura Unified School District':('https://www.venturausd.org/staff-careers/human-resources',
        'The configured RSS endpoint reports an invalid agency or disabled feed. Use the district’s official employment links.'),
    'State of Rhode Island (RI)':('https://www.governmentjobs.com/careers/rhodeisland',
        'The career page is accessible but RSS is unavailable. Review the official board directly.'),
}


def with_recovery_links(rows):
    result=[]
    for row in rows:
        item=dict(row)
        if item.get('status')=='Failed' and item.get('board') in ROUTES:
            item['recovery_url'],item['recovery_note']=ROUTES[item['board']]
        result.append(item)
    return result
