"""Stream complete RSS feeds without retaining the entire XML document."""
import xml.etree.ElementTree as ET
from source_http import open_response,remaining


def iter_rss_response(response,limit=32_000_000):
    parser=ET.XMLPullParser(events=('start','end'))
    total=0
    root_seen=False
    try:
        while True:
            remaining(10)
            chunk=response.read(min(65_536,limit-total+1))
            if not chunk:break
            total+=len(chunk)
            if total>limit:
                raise ValueError(f'RSS feed exceeds {limit} bytes; complete feed not retrieved')
            parser.feed(chunk)
            for event,element in parser.read_events():
                tag=str(element.tag).rsplit('}',1)[-1].lower()
                if not root_seen and event=='start':
                    root_seen=True
                    if tag not in ('rss','rdf','feed'):
                        raise ValueError('Unexpected RSS response root: '+tag[:55])
                if event=='end' and tag=='item':
                    yield element
                    element.clear()
        parser.close() # Missing closing tags must fail, not appear successful.
        if not root_seen: raise ValueError('Empty RSS response')
    except ET.ParseError as exc:
        raise ValueError('Malformed RSS XML: '+str(exc)[:80]) from exc


def iter_public_rss(request,timeout=10):
    with open_response(request,timeout=timeout) as response:
        yield from iter_rss_response(response)
