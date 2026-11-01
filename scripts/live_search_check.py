"""Run one real nationwide search through the app and report what happened.

Usage:  python scripts/live_search_check.py LABEL [path/to/app.py]

Drives the actual Streamlit app (Find Jobs -> Search, default filters, no
resume) against the live job sources, waits for the background search to
finish, then prints elapsed time, jobs fetched, ranked results, per-source
counts and any failed or partial boards. Results are also emitted as GitHub
notice annotations. Needs network access; not part of the unit tests.
"""
import os
import sys
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'search'
    app_path = Path(sys.argv[2] if len(sys.argv) > 2 else 'app.py').resolve()
    # The app imports its sibling modules and reads job_sources.json beside it.
    sys.path.insert(0, str(app_path.parent))
    os.chdir(app_path.parent)
    at = AppTest.from_file(str(app_path), default_timeout=120).run()
    assert not at.exception, [e.message for e in at.exception]
    at.radio(key='top_navigation').set_value('Find Jobs').run()
    search = next(b for b in at.button if b.label == 'Search')
    started = time.monotonic()
    search.click().run()
    task = at.session_state['active_search']
    while task.snapshot(False)['status'] == 'running' and time.monotonic() - started < 300:
        time.sleep(3)
    snap = task.snapshot(False)
    at.run()  # let the app consume the finished search
    stats = at.session_state['search_stats']
    results = at.session_state['search_results']
    health = stats.get('board_health') or []
    bad = [h for h in health if h.get('status') in ('Failed', 'Partial')]
    lines = [
        f"status={snap['status']} elapsed={snap.get('elapsed')}s first_results={snap.get('first_results_seconds')}s",
        f"fetched={stats.get('fetched')} ranked={len(results)} government={stats.get('government')}",
        f"sources reporting={len(health)} active={sum(h.get('status') == 'Active' for h in health)} "
        f"empty={sum(h.get('status') == 'Empty' for h in health)} failed/partial={len(bad)}",
        'by provider: ' + ', '.join(f'{k}={v}' for k, v in sorted((stats.get('sources') or {}).items())),
    ]
    lines += [f"  {h.get('status')}: {h.get('provider')} / {h.get('board')} - {str(h.get('error', ''))[:70]}"
              for h in bad[:40]]
    lines += ['top results: ' + ' | '.join(f"{r['title'][:40]} ({r['company'][:25]})" for r in results[:8])]
    for line in lines:
        print(line)
    body = '%0A'.join(x.replace('%', '%25') for x in lines)[:3900]
    print(f'::notice title=live search {label}::{body}')
    if snap['status'] != 'complete':
        print(f'::error title=live search {label}::search ended as {snap["status"]}')
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException:  # report the reason as an annotation, then fail
        import traceback
        tail = traceback.format_exc().strip().splitlines()[-8:]
        print('::error title=live search crashed::' + '%0A'.join(x.replace('%', '%25') for x in tail)[:3500])
        sys.exit(1)
