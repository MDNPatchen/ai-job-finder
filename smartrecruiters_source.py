"""Public SmartRecruiters pagination and bounded detail retrieval."""
from datetime import date,timedelta
from urllib.parse import quote,urlencode
from source_http import ContextPool,request_budget
from source_result import SourceRecords
from posting_metadata import declared_arrangement,affirmative


def fetch_board(board,getter,normalize,classify,parse_date,max_age,max_pages=50,max_details=100):
    token,employer,government=board
    root='https://api.smartrecruiters.com/v1/companies/'+quote(token)+'/postings'
    candidates=[];seen=set();pages=0;provider_records=0;truncated=False;issue=''
    with request_budget(60):
        for page in range(max_pages):
            try:
                data=getter(root+'?'+urlencode({'limit':100,'offset':page*100,'destination':'PUBLIC','country':'us'}),timeout=10)
                rows=data.get('content')
                if not isinstance(rows,list): raise ValueError('Missing postings content')
            except (OSError,ValueError,TypeError,KeyError) as exc:
                if not pages: raise
                issue=type(exc).__name__;break
            pages+=1;provider_records+=len(rows);new=0
            for item in rows:
                if not isinstance(item,dict) or not item.get('id'): continue
                if item['id'] in seen: continue
                seen.add(item['id']);new+=1
                if not classify(item.get('name')): continue
                posted=parse_date(item.get('releasedDate'))
                if not posted or not date.today()-timedelta(days=max_age)<=posted<=date.today(): continue
                place=item.get('location') or {}
                if str(place.get('country') or '').lower() not in ('us','usa','united states','united states of america'): continue
                style=declared_arrangement(item.get('locationType'))
                if style=='Remote' and not government: continue
                if affirmative(place.get('remote')) and style!='Hybrid' and not government: continue
                candidates.append(item)
            total=data.get('totalFound')
            if not rows or (isinstance(total,int) and len(seen)>=total) or (total is None and len(rows)<100): break
            if not new: issue='Provider repeated a page';break
        else: truncated=True
        truncated=truncated or len(candidates)>max_details
        def detail(item):
            try:
                data=getter(root+'/'+quote(str(item['id'])),timeout=8)
                sections=((data.get('jobAd') or {}).get('sections') or {})
                text='\n'.join(key+': '+str((sections.get(key) or {}).get('text') or '')
                             for key in ('jobDescription','qualifications','additionalInformation'))
                loc=item.get('location') or {}
                job=normalize(item.get('name'),(item.get('company') or {}).get('name') or employer,
                    data.get('postingUrl') or data.get('applyUrl'),
                    ', '.join(str(x) for x in (loc.get('city'),loc.get('region'),'United States') if x),
                    text,'SmartRecruiters',False,posted=item.get('releasedDate'),gov=government,
                    declared_style=declared_arrangement(data.get('locationType') or item.get('locationType')))
                return job
            except (OSError,ValueError,TypeError,KeyError): return None
        with ContextPool(max_workers=3) as pool:
            checked=list(pool.map(detail,candidates[:max_details]))
    return SourceRecords([j for j in checked if j],{'provider_records':provider_records,
        'page_limit':max_pages,'reported_total':total if 'total' in locals() else None,
        'pages':pages,'candidates':len(candidates),'details_attempted':len(checked),
        'failed_details':sum(j is None for j in checked),'truncated':truncated,'partial_error':issue})
