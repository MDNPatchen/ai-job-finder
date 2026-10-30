"""Bounded public requests with retries and propagated per-search deadlines."""
import contextvars
import json
import time
import ssl
import certifi
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

_deadline=contextvars.ContextVar('source_deadline',default=None)
_cancel=contextvars.ContextVar('source_cancel',default=None)


class SearchCancelled(RuntimeError):
    pass


@contextmanager
def cancellation_scope(event):
    token=_cancel.set(event)
    try: yield
    finally: _cancel.reset(token)


def check_cancelled():
    event=_cancel.get()
    if event is not None and event.is_set():
        raise SearchCancelled('Search cancelled')



class ContextPool(ThreadPoolExecutor):
    def submit(self,fn,/,*args,**kwargs):
        context=contextvars.copy_context()
        return super().submit(context.run,fn,*args,**kwargs)


@contextmanager
def request_budget(seconds):
    previous=_deadline.get()
    token=_deadline.set(min(previous,time.monotonic()+seconds) if previous else time.monotonic()+seconds)
    try: yield
    finally: _deadline.reset(token)


def remaining(timeout):
    check_cancelled()
    deadline=_deadline.get()
    if deadline is None: return timeout
    left=deadline-time.monotonic()
    if left<=0: raise TimeoutError('Search time budget reached')
    return min(timeout,left)


_tls_context=None
_tls_lock=Lock()


def trusted_context():
    # Retain host trust settings and add the pinned public CA bundle. Never
    # disable certificate or hostname verification for incomplete host stores.
    global _tls_context
    with _tls_lock:
        if _tls_context is None:
            context=ssl.create_default_context()
            context.load_verify_locations(cafile=certifi.where())
            _tls_context=context
        return _tls_context


def open_response(request,timeout=10):
    return urlopen(request,timeout=remaining(timeout),context=trusted_context())


def fetch_json(url,timeout=12,opener=None,sleep=time.sleep,headers=None):
    opener=opener or open_response
    request=Request(url,headers={'User-Agent':'AIJobFinder/3.2 personal career research',
                                 'Accept':'application/json',**(headers or {})})
    for attempt in range(3):
        try:
            with opener(request,timeout=remaining(timeout)) as response:
                raw=read_bounded(response)
            return json.loads(raw)
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2: raise
            retry=exc.headers.get('Retry-After','') if exc.headers else ''
            delay=min(2,float(retry)) if retry.isdigit() else .25*(2**attempt)
        except (URLError,TimeoutError,OSError):
            if attempt==2: raise
            delay=.25*(2**attempt)
        sleep(remaining(delay))


def read_bounded(response,limit=12_000_000,chunk_size=65_536):
    """Read a complete body or fail explicitly; never parse a cut-off prefix."""
    chunks=[]
    total=0
    while True:
        remaining(10)
        chunk=response.read(min(chunk_size,limit-total+1))
        if not chunk:
            return b''.join(chunks)
        total+=len(chunk)
        if total>limit:
            raise ValueError(f'Provider response exceeds {limit} bytes; complete feed not retrieved')
        chunks.append(chunk)
