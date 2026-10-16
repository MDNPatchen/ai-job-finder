"""Validate that a public government RSS vacancy belongs to its configured agency.

Several providers have been observed returning the same Boise vacancy in
other agencies' RSS responses. Trust the vacancy-specific official /careers/
slug, not the name of the feed that supplied it. In a conflict the safer
action is to exclude the record, never relabel the hiring employer.
"""
import re
from urllib.parse import urlsplit
from job_workflow import canonical_job_url

_VACANCY_PATH = re.compile(
    r"^/careers/([A-Za-z0-9_-]+)/jobs/(?:newprint/)?([0-9]{5,12})"
    r"(?:-[^/?#]*)?/?$", re.I)
_HOST_FOR_SOURCE = {
    "NEOGOV": "governmentjobs.com",
    "NEOED Schooljobs": "schooljobs.com",
}


def official_vacancy_agency(url, source):
    """Return the literal official agency slug only for a verified job URL."""
    host=_HOST_FOR_SOURCE.get(source)
    if not host:
        return ""
    try:
        parts=urlsplit(str(url or "").strip())
        hostname=(parts.hostname or "").lower()
        if (parts.scheme.lower()!="https" or
                hostname not in (host, "www."+host) or
                parts.username or parts.password):
            return ""
        match=_VACANCY_PATH.fullmatch(parts.path)
        return match.group(1).lower() if match else ""
    except (TypeError,ValueError):
        return ""


def belongs_to_configured_agency(url, agency_slug, source):
    """An unrecognized or contradictory URL is not attribution evidence."""
    slug=official_vacancy_agency(url,source)
    return bool(slug and slug==str(agency_slug or "").strip().lower())


def dedupe_vacancy_urls(jobs):
    """One displayed record per official vacancy, even across provider feeds.

    Preserve order and distinct requisition IDs. Fallback/summary directory
    URLs remain untouched (they should be filtered by direct-link settings).
    """
    seen=set()
    output=[]
    for job in jobs:
        uri=canonical_job_url(job.get("url"))
        source=job.get("source")
        valid_agency=official_vacancy_agency(job.get("url"),source)
        identity=("official-vacancy",uri) if (uri and valid_agency) else None
        if identity is not None:
            if identity in seen:
                continue
            seen.add(identity)
        output.append(job)
    return output
