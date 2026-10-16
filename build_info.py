"""Version identifiers for Job Finder qualification matching and evidence exports.

Bump MATCHING_ENGINE_VERSION whenever scoring, requirement extraction,
or exported record format changes.
"""
import re

MATCHING_ENGINE_VERSION = "3.1.4"


def needs_search_refresh(previous_version, current_version=MATCHING_ENGINE_VERSION):
    """Search rankings produced by earlier scoring code must not be reused."""
    return previous_version != current_version


def export_filename(kind, run_id, extension):
    """Version and UTC search ID make new downloads distinct from old ones."""
    if kind not in ("ranked", "detailed") or extension not in ("csv", "json"):
        raise ValueError("Unsupported export format")
    clean = re.sub(r"[^0-9TZ]", "", str(run_id or ""))[:20]
    if not clean:
        clean = "unknown"
    version = MATCHING_ENGINE_VERSION.replace(".", "")
    return f"job_qualification_breakdowns_{kind}_v{version}_{clean}.{extension}"
