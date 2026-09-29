#!/usr/bin/env python3
"""Compute or validate Twilio's X-Twilio-Signature, printing the exact string that was signed.

Algorithm (form-encoded POST): base64(HMAC-SHA1(auth_token, full_url + concat(sorted(name+value))))
Algorithm (JSON body):        URL contains ?bodySHA256=<hex sha256(raw body)>; signature covers the URL only.

Examples
  # Validate a form webhook (params as key=value pairs, repeat keys allowed)
  python validate_signature.py --url "https://example.com/sms" \
      --param From=+15551234567 --param Body="Hi there" --signature "abc123="

  # Validate from a raw form body captured in logs
  python validate_signature.py --url "https://example.com/sms" --form-body 'From=%2B1555...&Body=Hi' --signature "..."

  # JSON webhook (URL must already include bodySHA256)
  python validate_signature.py --url "https://example.com/hook?bodySHA256=..." --json-body-file body.json --signature "..."

  # Generate a signature to replay a request against your own endpoint
  python validate_signature.py --sign --url "https://example.com/sms" --param From=+1555 --param Body=Hi

Auth token is read from TWILIO_AUTH_TOKEN (never pass it on the command line in shared shells).
Use the Twilio SDK RequestValidator in production; this tool is for understanding and debugging.
"""
import argparse
import base64
import hashlib
import hmac
import os
import sys
from urllib.parse import parse_qsl, urlsplit, urlunsplit, parse_qs


def string_to_sign(url, params):
    s = url
    for name in sorted(params):
        for value in sorted(params[name]):
            s += name + value
    return s


def sign(token, data):
    return base64.b64encode(hmac.new(token.encode(), data.encode("utf-8"), hashlib.sha1).digest()).decode()


def url_variants(url):
    """SDKs try the URL with and without an explicit default port."""
    parts = urlsplit(url)
    variants = [url]
    host = parts.hostname or ""
    default = 443 if parts.scheme == "https" else 80
    if parts.port is None:
        netloc = parts.netloc.replace(host, f"{host}:{default}", 1)
        variants.append(urlunsplit(parts._replace(netloc=netloc)))
    elif parts.port == default:
        netloc = parts.netloc.replace(f":{default}", "", 1)
        variants.append(urlunsplit(parts._replace(netloc=netloc)))
    return variants


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="Full public URL Twilio requested, including query string")
    ap.add_argument("--param", action="append", default=[], help="name=value (repeatable)")
    ap.add_argument("--form-body", help="Raw application/x-www-form-urlencoded body")
    ap.add_argument("--json-body-file", help="File with the raw JSON body (bytes exactly as received)")
    ap.add_argument("--signature", help="X-Twilio-Signature header value to validate")
    ap.add_argument("--sign", action="store_true", help="Just print the signature for these inputs")
    a = ap.parse_args()

    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not token:
        sys.exit("Set TWILIO_AUTH_TOKEN (the account's primary Auth Token).")

    params = {}
    if a.json_body_file:
        raw = open(a.json_body_file, "rb").read()
        expected = hashlib.sha256(raw).hexdigest()
        got = parse_qs(urlsplit(a.url).query).get("bodySHA256", [None])[0]
        print(f"sha256(raw body) = {expected}")
        print(f"bodySHA256 in URL = {got}")
        if got != expected:
            print("MISMATCH: body hash differs -> body was modified/re-serialized, or wrong URL.")
    else:
        pairs = parse_qsl(a.form_body, keep_blank_values=True) if a.form_body else []
        for p in a.param:
            k, _, v = p.partition("=")
            pairs.append((k, v))
        for k, v in pairs:
            params.setdefault(k, []).append(v)

    results = []
    for u in url_variants(a.url):
        s = string_to_sign(u, params)
        results.append((u, s, sign(token, s)))

    for u, s, sig in results:
        print("\nURL variant :", u)
        print("Signed data :", s)
        print("Signature   :", sig)

    if a.sign:
        return
    if not a.signature:
        sys.exit("\nPass --signature to validate, or --sign to generate.")
    ok = any(hmac.compare_digest(sig, a.signature) for _, _, sig in results)
    print("\nRESULT:", "VALID" if ok else "INVALID")
    if not ok:
        print("Check: public https URL vs internal URL (proxy), trailing slash, query string, "
              "exact param values (decoded), primary vs secondary/subaccount Auth Token.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
