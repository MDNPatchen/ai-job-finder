"""The app's own source, for tests that inspect code rather than run it.

The app is split into app.py (entry point), app_core.py (logic) and
views/*.py (pages). Tests that look up a function or setting by name read
all of them as one module's worth of text.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ('app.py', 'app_core.py', *sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'views').glob('*.py')))


def app_source():
    return '\n\n'.join((ROOT / name).read_text(encoding='utf-8') for name in FILES)
