#!/usr/bin/env python3
"""Minimal raw-HTTP Twilio client that shows exactly what goes over the wire.

Features: Basic auth with API key (or Account SID/Auth Token), form encoding with repeated keys,
optional JSON bodies, automatic pagination for both API families (next_page_uri / meta.next_page_url),
retry with exponential backoff + jitter on 429/5xx, and a verbose trace of request/response.

Env: TWILIO_ACCOUNT_SID, and either TWILIO_API_KEY + TWILIO_API_SECRET or TWILIO_AUTH_TOKEN.
     Optional TWILIO_REGION / TWILIO_EDGE (e.g. ie1 / dublin) to rewrite hosts.

CLI examples
  python twilio_http.py POST /2010-04-01/Accounts/{AccountSid}/Messages.json \
      To=+15558675310 From=+15017122661 "Body=Hello from raw HTTP"
  python twilio_http.py GET "https://verify.twilio.com/v2/Services" --all
  python twilio_http.py GET "/2010-04-01/Accounts/{AccountSid}/Messages.json" PageSize=20 "DateSent>=2026-09-01" --all --max-pages 3
  python twilio_http.py POST https://content.twilio.com/v1/Content --json '{"friendly_name":"x","language":"en","types":{"twilio/text":{"body":"hi"}}}'
  python twilio_http.py GET "https://lookups.twilio.com/v2/PhoneNumbers/+14159929960" Fields=line_type_intelligence

Relative paths are resolved against https://api.twilio.com. "{AccountSid}" is substituted.
As a library: from twilio_http import TwilioHTTP; t = TwilioHTTP(); t.request("POST", path, data={...})
"""
import json
import os
import random
import sys
import time
from urllib.parse import quote, urlsplit, urlunsplit

import requests

RETRY_STATUSES = {429, 500, 502, 503, 504}


def _redact(h):
    return {k: ("<redacted>" if k.lower() == "authorization" else v) for k, v in h.items()}


class TwilioHTTP:
    def __init__(self, verbose=True, max_retries=4, timeout=30):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        key, secret = os.environ.get("TWILIO_API_KEY"), os.environ.get("TWILIO_API_SECRET")
        if key and secret:
            self.auth = (key, secret)
        else:
            self.auth = (self.account_sid, os.environ.get("TWILIO_AUTH_TOKEN", ""))
        if not all(self.auth):
            raise SystemExit("Set TWILIO_API_KEY/TWILIO_API_SECRET or TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN")
        self.region, self.edge = os.environ.get("TWILIO_REGION"), os.environ.get("TWILIO_EDGE")
        self.verbose, self.max_retries, self.timeout = verbose, max_retries, timeout
        self.s = requests.Session()

    def _url(self, path):
        path = path.replace("{AccountSid}", self.account_sid)
        url = path if path.startswith("http") else "https://api.twilio.com" + path
        parts = urlsplit(url)
        # Encode a literal '+' in the path (e.g. Lookup phone numbers) so it isn't read as a space.
        parts = parts._replace(path=quote(parts.path, safe="/:%"))
        if self.region and self.edge and parts.hostname.endswith(".twilio.com"):
            product = parts.hostname.split(".")[0]
            parts = parts._replace(netloc=f"{product}.{self.edge}.{self.region}.twilio.com")
        return urlunsplit(parts)

    def request(self, method, path, data=None, params=None, json_body=None):
        url = self._url(path)
        # data/params may be dict or list of tuples; lists allow repeated keys (MediaUrl, StatusCallbackEvent)
        for attempt in range(self.max_retries + 1):
            req = requests.Request(method, url, auth=self.auth, data=data, params=params, json=json_body)
            prep = self.s.prepare_request(req)
            if self.verbose:
                print(f"\n>>> {prep.method} {prep.url}", file=sys.stderr)
                for k, v in _redact(dict(prep.headers)).items():
                    print(f">>> {k}: {v}", file=sys.stderr)
                if prep.body:
                    b = prep.body.decode() if isinstance(prep.body, bytes) else prep.body
                    print(f">>>\n>>> {b}", file=sys.stderr)
            r = self.s.send(prep, timeout=self.timeout)
            if self.verbose:
                print(f"<<< {r.status_code} {r.reason}", file=sys.stderr)
                for h in ("Content-Type", "Twilio-Request-Id", "Twilio-Request-Duration",
                          "Twilio-Concurrent-Requests", "ETag", "X-Message-Id"):
                    if h in r.headers:
                        print(f"<<< {h}: {r.headers[h]}", file=sys.stderr)
            if r.status_code in RETRY_STATUSES and attempt < self.max_retries:
                # Caution: retrying a create after a 5xx can duplicate (no idempotency keys on most creates).
                if method != "GET" and r.status_code != 429:
                    if self.verbose:
                        print("<<< not retrying non-GET on 5xx to avoid duplicates", file=sys.stderr)
                    return r
                delay = min(30, 2 ** attempt) + random.uniform(0, 1)
                if self.verbose:
                    print(f"<<< retrying in {delay:.1f}s", file=sys.stderr)
                time.sleep(delay)
                continue
            return r
        return r

    def paginate(self, path, params=None, max_pages=None):
        """Yield records across pages for both 2010 (next_page_uri) and v1+ (meta.next_page_url) APIs."""
        url, pages = path, 0
        while url:
            r = self.request("GET", url, params=params)
            r.raise_for_status()
            body = r.json()
            params = None  # the next URL already carries the query
            if "meta" in body:  # product APIs
                key = body["meta"].get("key")
                yield from body.get(key, [])
                url = body["meta"].get("next_page_url")
            else:  # 2010 API
                key = next((k for k, v in body.items() if isinstance(v, list)), None)
                yield from body.get(key, []) if key else []
                nxt = body.get("next_page_uri")
                url = ("https://api.twilio.com" + nxt) if nxt else None
            pages += 1
            if max_pages and pages >= max_pages:
                break


def _parse_kv(args):
    out = []
    for a in args:
        k, sep, v = a.partition("=")
        if not sep:
            raise SystemExit(f"Expected key=value, got {a!r}")
        # support filters like "DateSent>=2026-09-01": partition on first '=' leaves 'DateSent>' as key
        out.append((k, v))
    return out


def main():
    argv = sys.argv[1:]
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    method, path, rest = argv[0].upper(), argv[1], argv[2:]
    all_pages = "--all" in rest
    max_pages = None
    json_body = None
    if "--max-pages" in rest:
        i = rest.index("--max-pages"); max_pages = int(rest[i + 1]); del rest[i:i + 2]
    if "--json" in rest:
        i = rest.index("--json"); json_body = json.loads(rest[i + 1]); del rest[i:i + 2]
    rest = [a for a in rest if a != "--all"]
    kv = _parse_kv(rest)
    t = TwilioHTTP()
    if all_pages and method == "GET":
        for i, rec in enumerate(t.paginate(path, params=kv, max_pages=max_pages)):
            print(json.dumps(rec))
        return
    r = t.request(method, path, data=kv if method != "GET" and not json_body else None,
                  params=kv if method == "GET" else None, json_body=json_body)
    try:
        print(json.dumps(r.json(), indent=2))
    except ValueError:
        print(r.text)
    sys.exit(0 if r.ok else 1)


if __name__ == "__main__":
    main()
