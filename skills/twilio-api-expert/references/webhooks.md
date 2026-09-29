# Twilio Webhooks

Contents: 1. Kinds of webhooks · 2. The request Twilio sends · 3. What to respond · 4. Signature validation (X-Twilio-Signature) · 5. Timeouts, retries & connection overrides · 6. Fallback URLs · 7. Ordering, duplicates & idempotency · 8. Local development · 9. Common failures

---

## 1. Kinds of webhooks

| Kind | Examples | Expects back |
|---|---|---|
| **Instruction webhooks** | Incoming call (`VoiceUrl`), incoming message (`SmsUrl`/Messaging Service `InboundRequestUrl`), `<Gather action>`, `<Dial action>` | **TwiML** (`text/xml`) |
| **Status callbacks** | Message `StatusCallback`, Call `StatusCallback`, `RecordingStatusCallback`, Conference `statusCallback` | Just `200`/`204` (body ignored) |
| **Product event webhooks** | Conversations pre/post events, TaskRouter `EventCallbackUrl` & `AssignmentCallbackUrl`, Verify events, Video room status, Studio | Product-specific (JSON instruction for TaskRouter assignment & Conversations pre-hooks, otherwise 200) |
| **Event Streams** | Sink type `webhook` | 200; CloudEvents JSON batches |

Default method is **POST, form-encoded** (configurable to GET → params in query string). Some newer products (Conversations v2/Orchestrator, Event Streams) send **JSON**.

## 2. The request Twilio sends

Common to voice and messaging: `AccountSid`, `From`, `To`, `ApiVersion`, plus geo hints (`FromCity`, `FromState`, `FromZip`, `FromCountry`, `ToCity`, … — best-effort, often empty).

**Incoming message**: `MessageSid` (also legacy `SmsSid`, `SmsMessageSid`), `MessagingServiceSid`, `Body`, `NumMedia`, `NumSegments`, `MediaUrl0..N`, `MediaContentType0..N`, `SmsStatus=received`. WhatsApp adds `ProfileName`, `WaId`, and for interactive replies `ButtonText`/`ButtonPayload`, location `Latitude`/`Longitude`, `ReferralBody`… With Advanced Opt-Out: `OptOutType` (STOP/HELP/START).

**Message status callback**: `MessageSid`, `MessageStatus` (`queued|sending|sent|delivered|undelivered|failed|read|canceled`…), `ErrorCode` (only on failure), `RawDlrDoneDate` (SMS, `YYMMDDhhmm`), `ChannelPrefix`, `EventType=READ` (WhatsApp/RCS read receipts).

**Incoming call**: `CallSid`, `CallStatus` (`ringing` on inbound), `Direction` (`inbound`, `outbound-api`, `outbound-dial`), `ForwardedFrom`, `CallerName` (if CNAM lookup enabled), `ParentCallSid`, `CallToken`.

**Call status callback** adds `CallDuration`, `Duration`, `Timestamp`, `CallbackSource=call-progress-events`, `SequenceNumber` (use it to order events), `SipResponseCode`, and `AnsweredBy` when AMD is on. Recording callbacks: `RecordingSid`, `RecordingUrl`, `RecordingStatus`, `RecordingDuration`, `RecordingChannels`, `RecordingSource`.

Media URLs (`MediaUrl0`, `RecordingUrl`) may require HTTP Basic auth if "Enforce HTTP Auth on Media URLs" is enabled.

## 3. What to respond

- Instruction webhooks: `200 OK`, `Content-Type: text/xml` (or `application/xml`), body a `<Response>` document. To accept a message without replying: `<?xml version="1.0" encoding="UTF-8"?><Response/>`. Returning JSON/HTML/plain text → 12300 (invalid content type) or 12100 (parse failure).
- TwiML responses must be ≤ 64 kB (11750).
- TwiML is **case-sensitive** (`<Say>`, not `<say>`). Twilio follows up to 10 HTTP redirects and honors cookies within a call.
- Status callbacks: return `204 No Content` (or `200` with empty `<Response/>`) quickly. Do heavy work async (queue it).
- Respond within ~15s total (default read timeout); aim for <1–2s. Voice callers hear silence while you think.
- A non-2xx response or timeout triggers the fallback URL (if set) and a Debugger error (11200 retrieval failure, 11205 connection failure, 11210 DNS, 11237 cert issue).

## 4. Signature validation (X-Twilio-Signature)

Twilio signs every webhook with **HMAC-SHA1**, key = your account's **primary Auth Token** (even if you use API keys for REST), output **Base64** → `X-Twilio-Signature` header.

**Form-encoded POST** — string to sign:
1. Start with the **full URL exactly as Twilio requested it** — scheme, host, path, *and query string*.
2. Sort all POST body params **alphabetically by name** (case-sensitive byte order).
3. Append each `name` immediately followed by its `value` (no separators). Repeated keys: each occurrence, in sorted value order.
4. `base64(hmac_sha1(auth_token, that_string))` must equal the header (compare in constant time).

**GET** (or no body): sign just the full URL with query string.

**JSON body** (`Content-Type: application/json`, e.g., some newer products): Twilio adds `bodySHA256=<hex sha256 of raw body>` to the URL query string and signs the URL only. Validate by (a) hashing the **raw bytes** of the body and comparing to `bodySHA256`, then (b) validating the URL signature. Don't parse the JSON first — reserialization changes bytes.

Use the SDK helper — Twilio explicitly recommends against hand-rolling because parameter sets evolve:
- Python: `from twilio.request_validator import RequestValidator; RequestValidator(token).validate(url, request.form, signature)` (JSON: `validate(url, raw_body, signature)`)
- Node: `twilio.validateRequest(token, signature, url, params)`; Express middleware `twilio.webhook()`; JSON: `validateRequestWithBody`.
- C#/Java/Go/PHP/Ruby: `RequestValidator` class in each SDK.
- Twilio Functions: set visibility **Protected** and validation is automatic.

**The #1 cause of mismatches is the URL.** Behind load balancers, API gateways, ngrok, or Kubernetes ingress, your app sees `http://internal-host:8080/path` while Twilio signed `https://public.example.com/path`. Reconstruct from `X-Forwarded-Proto`/`X-Forwarded-Host` or hardcode the public base URL. Other causes: port added/removed (SDKs try both with and without `:443`), trailing slash, query-string reordering by middleware, body already consumed/modified by a parser, using a secondary or wrong subaccount's Auth Token, URL containing basic-auth credentials (`https://user:pass@host` — the credentials are *not* part of the signed URL in current SDKs; test both if in doubt), and the `#fragment` connection overrides (fragments are not sent or signed).

Additional protections: HTTPS with a CA-signed cert (self-signed fails), optional HTTP Basic/Digest auth in the URL (`https://user:pass@example.com/hook`). **Don't IP-allowlist** — Twilio has no fixed webhook IP range.

`scripts/validate_signature.py` prints the exact signed string for debugging.

## 5. Timeouts, retries & connection overrides

Append a URL **fragment** to any webhook URL to tune how Twilio connects (fragments aren't sent to your server):

```
https://example.com/hook#ct=3000&rt=10000&tt=15000&rc=3&rp=5xx,ct,rt&sni=y&e=dublin
```

| Key | Meaning | Range | Default |
|---|---|---|---|
| `ct` | TCP connect timeout (ms) | 100–10000 | 5000 |
| `rt` | Read timeout per response packet (ms) | 100–15000 | 15000 |
| `tt` | Total time incl. retries (ms) | 100–15000 | 15000 |
| `rc` | Retry count | 0–5 | 1 |
| `rp` | Retry on: `4xx`,`5xx`,`ct`,`rt`,`all` (comma list) | | `ct` |
| `sni` | Send SNI on TLS | `y`/`n` | `y` |
| `e` | Egress edge(s), e.g., `dublin,sydney` | | `ashburn` |

By default Twilio only retries once on connect failure — a 500 from your server is **not** retried unless you set `rp=5xx`. Retried requests carry the same `I-Twilio-Idempotency-Token`.

Account-wide defaults and rules can also be managed via Webhook settings/rules/auth profiles (newer features under `/docs/usage/webhooks/*`).

## 6. Fallback URLs

`VoiceFallbackUrl`, `SmsFallbackUrl`, Messaging Service `FallbackUrl`: requested when the primary fails (non-2xx, timeout, invalid TwiML). Twilio adds `ErrorCode` and `ErrorUrl` params. Host it on different infrastructure (e.g., a Twilio Function or TwiML Bin) so it survives your outage.

## 7. Ordering, duplicates & idempotency

- **Status callbacks can arrive out of order** (e.g., `delivered` before `sent`). Never assume sequence; keep the "furthest" state using a rank (`queued<sending<sent<delivered/undelivered/failed<read`) or, for calls, `SequenceNumber`/`Timestamp`.
- Expect **duplicates**. Make handlers idempotent: upsert keyed by `MessageSid`/`CallSid`+status, or dedupe on `I-Twilio-Idempotency-Token`.
- Acknowledge fast, process async.

## 8. Local development

- Expose localhost with ngrok / Cloudflare Tunnel / Twilio CLI (`twilio phone-numbers:update +1… --sms-url http://localhost:3000/sms` auto-creates an ngrok tunnel).
- Signature validation with tunnels: validate against the public https URL.
- Replay: Console Debugger shows the request/response; you can copy params and `curl -X POST -d …` your endpoint. Compute a valid signature with `scripts/validate_signature.py --sign`.

## 9. Common failures

| Symptom | Likely cause |
|---|---|
| 11200 / 11205 in Debugger | Endpoint unreachable, slow, non-2xx, bad TLS |
| 12100 Document parse failure | Invalid XML, HTML error page returned, BOM, unescaped `&` in `<Say>` |
| 12300 Invalid Content-Type | Returned `application/json` or `text/html` to a TwiML webhook |
| Signature mismatch only in prod | Proxy URL rewrite; see §4 |
| Reply sent twice | Retries on slow handler; not idempotent |
| No inbound webhooks | Number attached to a Messaging Service whose inbound setting overrides the number (`UseInboundWebhookOnNumber`), or number points to a Studio Flow/TwiML App |
