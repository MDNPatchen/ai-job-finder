"""Named Find Jobs filter sets, saved with the tracker and rerun in one click.

A saved search stores only the form's own values, keyed by the widgets'
session keys. Values are checked against the form's current options when
loaded, so a renamed option can never break the page.
"""
import re

MAX_SEARCHES = 20
# widget key -> kind ('text' | 'choice' | 'multi' | 'int' | 'bool')
FILTER_FIELDS = {
    'f_search': 'text', 'f_state': 'choice', 'f_work': 'choice', 'f_scope': 'choice',
    'f_employer_scope': 'choice', 'f_include': 'multi', 'f_exclude': 'multi',
    'f_seniority': 'multi', 'f_minsal': 'int', 'f_unknownpay': 'bool', 'f_verified': 'bool',
}


def clean_value(kind, value):
    if kind == 'text' and isinstance(value, str):
        return value.strip()[:120]
    if kind == 'choice' and isinstance(value, str) and len(value) <= 120:
        return value
    if kind == 'multi' and isinstance(value, list):
        return [v for v in value if isinstance(v, str) and len(v) <= 120][:60]
    if kind == 'int' and isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0, min(10_000_000, int(value)))
    if kind == 'bool' and isinstance(value, bool):
        return value
    return None


def clean_saved_searches(items):
    """Validate a stored list; drop anything malformed rather than failing a restore."""
    if not isinstance(items, list):
        return []
    out, names = [], set()
    for item in items[:MAX_SEARCHES]:
        if not isinstance(item, dict):
            continue
        name = re.sub(r'\s+', ' ', str(item.get('name') or '')).strip()[:60]
        filters = item.get('filters') if isinstance(item.get('filters'), dict) else {}
        clean = {}
        for key, kind in FILTER_FIELDS.items():
            if key in filters:
                value = clean_value(kind, filters[key])
                if value is not None:
                    clean[key] = value
        if name and clean and name.casefold() not in names:
            names.add(name.casefold())
            out.append({'name': name, 'filters': clean})
    return out


def capture(state):
    """The form's current values, as stored in a saved search."""
    out = {}
    for key, kind in FILTER_FIELDS.items():
        if key in state:
            value = clean_value(kind, state[key])
            if value is not None:
                out[key] = value
    return out


def upsert(items, name, filters):
    """Add or replace a saved search by name (case-insensitive), newest first."""
    name = re.sub(r'\s+', ' ', str(name or '')).strip()[:60]
    if not name or not filters:
        raise ValueError('Give the search a name')
    kept = [s for s in clean_saved_searches(items) if s['name'].casefold() != name.casefold()]
    return clean_saved_searches([{'name': name, 'filters': filters}, *kept])


def remove(items, name):
    return [s for s in clean_saved_searches(items) if s['name'].casefold() != str(name).casefold()]


def apply(state, filters, options):
    """Set widget values before the form renders; skip values no longer offered.

    options: {widget key: list of valid choices} for 'choice' and 'multi' fields.
    """
    for key, kind in FILTER_FIELDS.items():
        if key not in filters:
            continue
        value = clean_value(kind, filters[key])
        if value is None:
            continue
        if kind == 'choice' and value not in options.get(key, ()):
            continue
        if kind == 'multi':
            value = [v for v in value if v in options.get(key, ())]
        state[key] = value
