"""Small, thread-safe cache of public provider JSON, independent of the UI."""
from collections import OrderedDict
from copy import deepcopy
from threading import Condition
from time import monotonic
import json
from source_http import check_cancelled


class PublicJSONCache:
    def __init__(self,ttl=900,max_bytes=32_000_000):
        self.ttl=ttl;self.max_bytes=max_bytes
        self.entries=OrderedDict();self.inflight=set();self.bytes=0
        self.condition=Condition()

    def get(self,key,fetch):
        with self.condition:
            while key in self.inflight:
                check_cancelled();self.condition.wait(.1)
            check_cancelled()
            entry=self.entries.get(key)
            if entry and entry[0]>monotonic():
                self.entries.move_to_end(key)
                value=entry[1]
                cached=True
            else:
                if entry:self.bytes-=self.entries.pop(key)[2]
                self.inflight.add(key);cached=False
        if cached:return deepcopy(value)
        try:
            value=fetch()
            size=len(json.dumps(value,ensure_ascii=False).encode())
            if size<=self.max_bytes:
                stored=deepcopy(value)
                with self.condition:
                    while self.entries and self.bytes+size>self.max_bytes:
                        self.bytes-=self.entries.popitem(last=False)[1][2]
                    self.entries[key]=(monotonic()+self.ttl,stored,size)
                    self.bytes+=size
            return value
        finally:
            with self.condition:
                self.inflight.discard(key);self.condition.notify_all()


public_json=PublicJSONCache()
