"""Separate operational failures from deliberate source coverage boundaries."""
def coverage_summary(rows):
    groups={key:[] for key in ('failed','incomplete','capped','bounded')}
    for row in rows:
        name=str(row.get('board') or row.get('provider') or 'Unknown source')
        if row.get('status')=='Failed': groups['failed'].append(name)
        elif row.get('failed_details') or row.get('partial_error'): groups['incomplete'].append(name)
        elif row.get('truncated'): groups['capped'].append(name)
        elif row.get('bounded_coverage'): groups['bounded'].append(name)
        elif row.get('status')=='Partial': groups['incomplete'].append(name)
    return {key:sorted(set(value)) for key,value in groups.items()}


def coverage_messages(rows):
    groups=coverage_summary(rows)
    messages=[]
    for key,level,label in (
        ('failed','warning','Sources unavailable'),
        ('incomplete','warning','Sources with request or detail failures'),
        ('capped','info','Sources that reached a retrieval limit'),
        ('bounded','caption','Sources using selected keyword coverage')):
        names=groups[key]
        if names:
            shown=', '.join(names[:5])
            if len(names)>5: shown+=f' and {len(names)-5} more'
            messages.append((level,f'{label} ({len(names)}): {shown}. '+
                ('Returned jobs are still available. See source coverage for details.' if level=='warning' else
                 'Additional postings may exist outside this search.')))
    return messages
