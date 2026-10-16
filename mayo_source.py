"""Free, bounded Mayo Clinic public career-page reader.

Uses only https://jobs.mayoclinic.org/search-jobs and /job/ detail pages.
It does not call an unofficial protected JSON endpoint or bypass access blocks.
Site layout changes or blocked requests are reported as provider errors.
"""
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit, unquote
from urllib.request import Request, urlopen

ORIGIN = "https://jobs.mayoclinic.org"
SEARCH = ORIGIN + "/search-jobs"
KEYWORDS = ("operations", "director", "business development", "supply chain", "manager")
MAX_DETAILS = 30
ROLE = re.compile(
    r"\b(?:director|manager|chief|administrat\w*|operations?|logistics|"
    r"distribution|business|finance|revenue|marketing|supply chain|project|"
    r"program|partnerships?|strategy|strategic|fleet|facilities)\b", re.I)
JOB_PATH = re.compile(r"^/job/[^/?#]+/[^/?#]+/33647/\d+/?$", re.I)
STATE = {"Minnesota": "MN", "Wisconsin": "WI", "Arizona": "AZ",
         "Florida": "FL", "Mississippi": "MS", "Iowa": "IA"}
LOC = re.compile(
    r"\b([A-Z][A-Za-z' .-]{1,45}),\s*(Minnesota|Wisconsin|Arizona|Florida|Mississippi|Iowa)\b")


class CareerPage(HTMLParser):
    """Extract public links and display text without third-party libraries."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.words, self.titles = [], [], []
        self.link, self.h1, self.head = None, False, []
        self.hidden = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            url = urljoin(ORIGIN, attrs.get("href") or "")
            parsed = urlsplit(url)
            if (parsed.scheme == "https" and parsed.netloc == "jobs.mayoclinic.org"
                    and JOB_PATH.fullmatch(parsed.path)):
                self.link = [url, []]
        if tag == "h1":
            self.h1, self.head = True, []
        if tag in ("script", "style"):
            self.hidden = tag

    def handle_data(self, text):
        if self.hidden:
            return
        if self.link is not None:
            self.link[1].append(text)
        if self.h1:
            self.head.append(text)
        if text.strip():
            self.words.append(text.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self.link is not None:
            self.links.append((self.link[0], " ".join(self.link[1]).strip()))
            self.link = None
        if tag == "h1":
            title = " ".join(self.head).strip()
            if title:
                self.titles.append(title)
            self.h1 = False
        if tag == self.hidden:
            self.hidden = ""


def parse_page(payload):
    page = CareerPage()
    page.feed(payload.decode("utf-8", "replace") if isinstance(payload, bytes) else payload)
    page.close()
    return page


def read_html(url, timeout=8):
    request = Request(url, headers={
        "User-Agent": "PersonalCareerResearch/1.0 (individual job search)",
        "Accept": "text/html,application/xhtml+xml"})
    with urlopen(request, timeout=timeout) as response:
        if "html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Mayo returned non-HTML content")
        return response.read(2_500_000)


def _title_from_job_url(url):
    """Derive the published job role from Mayo's own job-specific URL slug.

    The site's general-purpose marketing heading is sometimes 'Breakthrough'
    rather than a vacancy title. Never use a marketing slogan as a role.
    """
    path=urlsplit(url).path
    if not JOB_PATH.fullmatch(path):
        return ''
    slug=unquote(path.strip('/').split('/')[2])
    parts=[p for p in re.split(r'[-_]+',slug) if p]
    acronyms={'it','hr','rn','lpn','np','rn','mcl','rpa','ai','ehr','emr','cfo','cio'}
    return ' '.join(part.upper() if part.casefold() in acronyms
                    else part.capitalize() for part in parts)


def _job_title(page, url, search_title=''):
    """Prefer a real matching role heading; fall back to official URL slug."""
    canonical=_title_from_job_url(url)
    canonical_tokens=set(re.findall(r'[a-z0-9]+',canonical.casefold()))
    def valid(candidate):
        if not candidate or len(candidate)>120 or not ROLE.search(candidate):
            return False
        tokens=set(re.findall(r'[a-z0-9]+',candidate.casefold()))
        # Prevent advertising headings and unrelated recommended jobs
        # from becoming the role of this particular posting.
        return (not canonical_tokens or
                len(canonical_tokens & tokens)>=max(1,min(2,len(canonical_tokens))))
    for heading in page.titles:
        if valid(heading):
            return heading.strip()
    if valid(search_title):
        # Search-anchor text may contain a city or schedule after the role.
        # The URL slug remains the clean authoritative fallback.
        normalized=' '.join(search_title.split())
        tokens=set(re.findall(r'[a-z0-9]+',normalized.casefold()))
        if len(normalized)<=75 and len(tokens-canonical_tokens)<=1:
            return normalized
    return canonical


def parse_detail(payload, url, search_title=''):
    page = parse_page(payload)
    body = " ".join(page.words)
    # Stop before sidebar recommendations: those can contain nursing/RN
    # job names that are NOT requirements of this individual posting.
    body = re.split(r"\b(?:Jobs for you|Similar Jobs|Recently Viewed Jobs|"
                    r"Insights from previous hires|Top Matches for You)\b",
                    body, maxsplit=1, flags=re.I)[0]
    title = _job_title(page,url,search_title)
    date = re.search(
        r"(?:Date posted|Posting Date)\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
        body, re.I)
    place = LOC.search(body[:3000])
    location = (f"{place.group(1).strip()}, {STATE[place.group(2)]}" if place else "")
    if not location:
        alt = re.search(
            r"\bCity\s+([A-Za-z .-]{2,36})\s+State\s+(MN|WI|AZ|FL|MS|IA)\b",
            body[:5500])
        if alt:
            location = f"{alt.group(1).strip()}, {alt.group(2)}"
    if not title or not date or not location:
        return None
    hybrid = bool(re.search(
        r"\b(?:hybrid\s+(?:position|role|schedule|work|arrangement)|"
        r"(?:position|role|schedule|work)\s+(?:is\s+)?hybrid|"
        r"Flexibility of both remote and on-site work)\b", body, re.I))
    explicit = re.search(
        r'\bRemote Eligible\s*[:\-]?\s*(On Site|On-Site|Hybrid|Remote)\b',
        body[:4500], re.I)
    remote = bool(re.search(r"\bRemote\s*:\s*(?:Yes|True)\b", body[:2500], re.I))
    if explicit:
        response = explicit.group(1).lower().replace('-', ' ')
        style = ('On-site' if response == 'on site' else
                 'Hybrid' if response == 'hybrid' else 'Remote')
    else:
        style = 'Hybrid' if hybrid else 'Remote' if remote else ''
    salary = re.search(
        r"Compensation Detail\s+(.{0,190}?)(?:Benefits Eligible|Schedule|Hours/Pay Period|$)",
        body, re.I)
    raw_date = date.group(1)
    posted = (datetime.strptime(raw_date, "%m/%d/%Y").date().isoformat()
              if "/" in raw_date else raw_date)
    return {"title": title, "url": url, "location": location,
            "date": posted, "description": body[:9000],
            "salary": salary.group(1).strip() if salary else "",
            "work_style": style}


def fetch_mayo_jobs(fetcher=read_html, max_details=MAX_DETAILS):
    """Search employer pages by leadership terms; check details before returning."""
    candidates, successful, search_failures = {}, 0, []
    for term in KEYWORDS:
        url = SEARCH + "?" + urlencode({"k": term, "orgIds": "33647"})
        try:
            page = parse_page(fetcher(url))
            successful += 1
            for href, title in page.links:
                if ROLE.search(title):
                    candidates.setdefault(href, title)
        except Exception as exc:
            search_failures.append(f"{term}: {type(exc).__name__}")
    if not successful:
        raise ValueError("Mayo search pages unavailable: " + ", ".join(search_failures))
    if not candidates:
        raise ValueError("Mayo search HTML returned no recognized jobs; source layout may have changed")

    def relevance(item):
        text = item[1]
        executive = bool(re.search(r"\b(?:director|chief|vice president|general manager)\b", text, re.I))
        manager = bool(re.search(r"\bmanager\b", text, re.I))
        operations = bool(re.search(
            r"\b(?:business development|operations|supply chain|logistics|finance|"
            r"strategy|partnership|distribution|administration)\b", text, re.I))
        return (-(10 * executive + 6 * manager + 5 * operations), text.casefold())

    chosen = sorted(candidates.items(), key=relevance)[:min(max_details, MAX_DETAILS)]
    jobs, errors = [], []
    with ThreadPoolExecutor(max_workers=5) as pool:
        pending = {pool.submit(fetcher, link): (link, search_title)
                   for link, search_title in chosen}
        for future in as_completed(pending):
            link, search_title = pending[future]
            try:
                parsed = parse_detail(future.result(), link, search_title)
                if parsed:
                    jobs.append(parsed)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {str(exc)[:70]}")
    if not jobs:
        raise ValueError("Mayo details were inaccessible or lacked dates/locations: " +
                         (errors[0] if errors else "no usable detail records"))
    return jobs
