"""Bounded, best-effort official NEOGOV bulletin retrieval.

Uses the verified public /careers/<agency>/jobs/newprint/<id> route derived
from an *existing* GovernmentJobs/SchoolJobs vacancy URL. No scraping of
search engines, guessed job IDs, credentials, or paid APIs. An inaccessible
or ambiguous bulletin leaves the original listing untouched and visibly
incomplete. The candidate set is bounded to keep nationwide searches usable.
"""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import re

_ALLOWED={"www.governmentjobs.com","www.schooljobs.com"}
_OFFICIAL_URL=re.compile(r"^/careers/([A-Za-z0-9_-]+)/jobs/(?:newprint/)?(\d{5,11})(?:[-/].*)?$",re.I)
_BLOCK={"script","style","svg","noscript","form","nav","footer","header"}
_HEADINGS=re.compile(
    r"(?im)^\s*(?:position description|job responsibilities|duties and responsibilities|"
    r"(?:minimum|required|desired|preferred)?\s*qualifications|"
    r"additional information|supplemental questionnaire)\s*:?\s*$")
_QUALIFICATIONS=re.compile(
    r"(?im)^\s*(?:minimum qualifications?|required qualifications?|qualifications?)\s*:?\s*$")


def official_bulletin_url(vacancy_url):
    """Only canonical, vacancy-specific GovernmentJobs/SchoolJobs URLs."""
    parts=urlsplit(str(vacancy_url or ""))
    if parts.scheme!="https" or parts.hostname not in _ALLOWED or parts.username or parts.password:
        return ""
    match=_OFFICIAL_URL.fullmatch(parts.path.rstrip("/"))
    if not match:
        return ""
    # The print route is part of the same provider's official vacancy page.
    return "https://"+parts.hostname+"/careers/"+match[1]+"/jobs/newprint/"+match[2]


class _PlainBulletin(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._hidden=0
        self._chunks=[]
    def handle_starttag(self,tag,attrs):
        if self._hidden:
            if tag in _BLOCK:
                self._hidden+=1
            return
        if tag in _BLOCK:
            self._hidden=1
            return
        if tag in ("p","div","h1","h2","h3","h4","h5","li","tr","br","section","article","dt","dd"):
            self._chunks.append("\n")
    def handle_endtag(self,tag):
        if self._hidden:
            if tag in _BLOCK:
                self._hidden-=1
            return
        if tag in ("p","h1","h2","h3","h4","h5","li","tr","section","article"):
            self._chunks.append("\n")
    def handle_data(self,data):
        if not self._hidden:
            self._chunks.append(data)
    def text(self):
        raw="".join(self._chunks)
        lines=[re.sub(r"[ \t]+"," ",x).strip() for x in raw.splitlines()]
        return "\n".join(x for x in lines if x)


def _looks_like_this_vacancy(text,title):
    if not _QUALIFICATIONS.search(text) or len(text)<850:
        return False
    # Print bulletins must actually refer to this vacancy, not an error or
    # an agency-wide jobs index with some unrelated qualifications.
    heading="\n".join(text.splitlines()[:90]).casefold()
    words=[w for w in re.findall(r"[a-z0-9]+",str(title or "").casefold())
           if len(w)>3 and w not in {"manager","director","senior","chief","assistant","section"}]
    if not words:
        words=[w for w in re.findall(r"[a-z0-9]+",str(title or "").casefold()) if len(w)>3]
    return bool(words) and (sum(w in heading for w in words)>=max(1,(len(words)+1)//2))


def parse_bulletin_html(html,title):
    raw=str(html or "")
    if not raw or len(raw)>1_500_000:
        return ""
    parser=_PlainBulletin()
    try:
        parser.feed(raw)
    except (ValueError,AssertionError):
        return ""
    text=parser.text()
    if not _looks_like_this_vacancy(text,title):
        return ""
    # Preserve section headings for required-vs-preferred scope detection.
    begin=re.search(r"(?im)^\s*position description\s*$",text)
    if begin:
        text=text[begin.start():]
    end=re.search(r"(?im)^\s*(?:supplemental questionnaire|equal employment opportunity"
                  r"|contact information)\s*$",text)
    if end:
        text=text[:end.start()]
    text=text[:30000].strip()
    return text if _QUALIFICATIONS.search(text) and len(text)>800 else ""


def fetch_official_bulletin(job, timeout=7, opener=urlopen):
    url=official_bulletin_url(job.get("url"))
    if not url:
        return ""
    request=Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; FreeCareerResearch/3.1)",
        "Accept":"text/html,application/xhtml+xml"})
    try:
        with opener(request,timeout=timeout) as resp:
            # Don't trust automatic redirects to other domains.
            dest=urlsplit(resp.geturl())
            if dest.scheme!="https" or dest.hostname not in _ALLOWED:
                return ""
            mime=(resp.headers.get("Content-Type") or "").casefold()
            if mime and "html" not in mime:
                return ""
            payload=resp.read(1_500_001)
    except (OSError,ValueError,TimeoutError,TypeError):
        return ""
    if len(payload)>1_500_000:
        return ""
    return parse_bulletin_html(payload.decode("utf-8",errors="replace"),
                               job.get("title"))


def short_or_partial(job):
    desc=str(job.get("description") or "")
    if job.get("source") not in ("NEOGOV","NEOED Schooljobs"):
        return False
    return (len(desc)<2300 or not re.search(
        r"\b(?:minimum qualifications|qualifications|certifications required)\b",
        desc,re.I))


def enrich_priority_government_jobs(original_jobs, ranked_results,
                                   limit=28, fetch=fetch_official_bulletin):
    """Return a NEW list plus diagnostics; no mutation of cached feed records.

    Attempt only the highest-ranked short government postings with authentic
    provider URLs. Unretrievable postings stay visibly 'summary only'. A
    second ranking pass must follow because the complete bulletin can
    introduce non-transferable required qualifications.
    """
    picks=[]
    seen=set()
    for job in ranked_results:
        if len(picks)>=limit:
            break
        if not short_or_partial(job):
            continue
        url=official_bulletin_url(job.get("url"))
        if url and url not in seen:
            picks.append(job)
            seen.add(url)
    results={}
    if picks:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for job,desc in zip(picks,pool.map(fetch,picks)):
                if desc and len(desc)>len(str(job.get("description") or ""))+150:
                    results[job["url"]]=desc
    output=[]
    for item in original_jobs:
        new=dict(item)
        if new.get("url") in results:
            new["description"]=results[new["url"]]
            new["description_source"]="Official full public job bulletin"
        elif short_or_partial(new):
            new["description_source"]="RSS summary only — important requirements may be missing"
        elif new.get("source") in ("NEOGOV","NEOED Schooljobs"):
            new["description_source"]="Provider RSS text — completeness not verified"
        else:
            new.setdefault("description_source","Employer posting details as supplied by provider")
        output.append(new)
    return output,{"attempted":len(picks),"full_bulletins":len(results),
                   "summary_only":sum(v.get("description_source","").startswith("RSS summary")
                                      for v in output)}
