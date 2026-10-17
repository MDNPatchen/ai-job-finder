"""Per-session background work. Workers never read or write Streamlit state."""
from copy import deepcopy
from threading import Event, Lock, Thread
from time import monotonic
from source_http import cancellation_scope, SearchCancelled


class SearchTask:
    def __init__(self, worker, fingerprint):
        self.fingerprint = fingerprint
        self.cancel_event = Event()
        self._lock = Lock()
        self._snapshot = {'revision': 0, 'status': 'running', 'payload': None,
                          'message': 'Contacting job sources', 'elapsed': 0}
        self.started = monotonic()
        self.thread = Thread(target=self._run, args=(worker,), daemon=True)
        self.thread.start()

    def publish(self, payload=None, message=None):
        with self._lock:
            if payload is not None:
                if payload.get('matches') and 'first_results_seconds' not in self._snapshot:
                    self._snapshot['first_results_seconds']=round(monotonic()-self.started,1)
                self._snapshot['payload'] = deepcopy(payload)
            if message is not None:
                self._snapshot['message'] = message
            self._snapshot['revision'] += 1

    def _run(self, worker):
        try:
            with cancellation_scope(self.cancel_event):
                worker(self)
            status = 'cancelled' if self.cancel_event.is_set() else 'complete'
            message = 'Search stopped; completed results retained' if status == 'cancelled' else 'Search complete'
        except SearchCancelled:
            status, message = 'cancelled', 'Search stopped; completed results retained'
        except Exception as exc:
            status, message = 'failed', 'Search interrupted: ' + type(exc).__name__ + '; completed results retained'
        with self._lock:
            self._snapshot.update(status=status, message=message, elapsed=round(monotonic()-self.started,1))
            self._snapshot['revision'] += 1

    def cancel(self):
        self.cancel_event.set()

    def snapshot(self, include_payload=True):
        with self._lock:
            value = deepcopy(self._snapshot if include_payload else {k:v for k,v in self._snapshot.items() if k!='payload'})
        if value['status']=='running': value['elapsed'] = round(monotonic() - self.started, 1)
        return value
