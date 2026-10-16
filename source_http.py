"""Bounded public requests with retries and propagated per-search deadlines."""
import contextvars
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

_deadline=contextvars.ContextVar('source_deadline',default=None)


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
    deadline=_deadline.get()
    if deadline is None: return timeout
    left=deadline-time.monotonic()
    if left<=0: raise TimeoutError('Search time budget reached')
    return min(timeout,left)


def open_response(request,timeout=10):
    return urlopen(request,timeout=remaining(timeout))


def fetch_json(url,timeout=12,opener=None,sleep=time.sleep):
    opener=opener or open_response
    request=Request(url,headers={'User-Agent':'AIJobFinder/3.2 personal career research','Accept':'application/json'})
    for attempt in range(3):
        try:
            with opener(request,timeout=remaining(timeout)) as response:
                raw=response.read(12_000_001)
            if len(raw)>12_000_000: raise ValueError('Provider response exceeds 12 MB')
            return json.loads(raw)
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2: raise
            retry=exc.headers.get('Retry-After','') if exc.headers else ''
            delay=min(2,float(retry)) if retry.isdigit() else .25*(2**attempt)
        except (URLError,TimeoutError,OSError):
            if attempt==2: raise
            delay=.25*(2**attempt)
        sleep(remaining(delay))
