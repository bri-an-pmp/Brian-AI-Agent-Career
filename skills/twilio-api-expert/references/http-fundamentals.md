# Twilio HTTP Fundamentals

Contents: 1. Hosts & versions · 2. Authentication · 3. Request encoding · 4. Responses & dates · 5. Pagination · 6. Errors & status codes · 7. Rate limits, concurrency, retries · 8. Idempotency & conflicts · 9. Regions & edges · 10. Subaccounts · 11. Useful headers · 12. Debugging checklist

---

## 1. Hosts & versions

| Family | Base | Formats |
|---|---|---|
| 2010 "core" API | `https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/{Resource}.json` | XML (default), JSON (`.json`), CSV (`.csv`) |
| Product APIs | `https://{product}.twilio.com/v{N}/{Resource}` | JSON only; no extension |

Common product hosts: `messaging.twilio.com/v1` (Services, Tollfree Verifications, Brand/Campaign), `verify.twilio.com/v2`, `lookups.twilio.com/v2`, `conversations.twilio.com/v1`, `studio.twilio.com/v2`, `serverless.twilio.com/v1`, `taskrouter.twilio.com/v1`, `sync.twilio.com/v1`, `video.twilio.com/v1`, `events.twilio.com/v1`, `content.twilio.com/v1`, `trusthub.twilio.com/v1`, `numbers.twilio.com/v2` (regulatory bundles, hosted numbers), `voice.twilio.com/v1` (dialing permissions, BYOC), `iam.twilio.com/v1` (keys), `oauth.twilio.com/v2`, `insights.twilio.com/v1`, `monitor.twilio.com/v1` (alerts, events), `pricing.twilio.com/v2`, `accounts.twilio.com/v1` (credentials, auth-token promotion).

The account SID is in the URL path for 2010 resources but *not* for product APIs (they infer the account from credentials).

## 2. Authentication

**HTTP Basic** — `Authorization: Basic base64(username:password)`:

| Username | Password | Use |
|---|---|---|
| API Key SID `SK…` | API Key Secret | Recommended for all server-to-server calls |
| Account SID `AC…` | Auth Token | Root credential; needed for Accounts API, Auth Token promotion, test credentials; also the HMAC key for webhook signatures |

API key types: **Main** (full access, equivalent to Auth Token), **Standard** (everything except `/Accounts` and `/Keys` resources), **Restricted** (fine-grained permissions; cannot mint Access Tokens yet). The secret is shown once at creation. Keys are **region-scoped** — a US1 key gets `401`/20003 against IE1/AU1.

Create a key over HTTP: `POST https://iam.twilio.com/v1/Keys` with `AccountSid=AC…&FriendlyName=…` (Standard/Restricted), or `POST /2010-04-01/Accounts/{sid}/Keys.json`.

Rotate the Auth Token safely: create a secondary token (Console or `accounts.twilio.com/v1/AuthTokens/Secondary`), deploy it, then promote (`POST accounts.twilio.com/v1/AuthTokens/Promote`). Remember webhook signature validation uses the *primary* token — rotate validators at the same time.

**OAuth 2.0** (GA): `POST https://oauth.twilio.com/v2/token`, form-encoded `grant_type=client_credentials&client_id=…&client_secret=…` → `{"access_token": "...", "token_type": "Bearer", "expires_in": 3600}`. Then `Authorization: Bearer <token>`. Also supports `authorization_code` and `refresh_token`. Recent SDK versions support it natively. Cache the token and refresh before expiry.

**Access Tokens (JWT)** for client SDKs (Voice JS/iOS/Android, Video, Conversations, Sync): signed HS256 with an API key secret (never the Auth Token), header `cty: twilio-fpa;v=1`, `iss` = API key SID, `sub` = Account SID, `grants` with `identity` plus e.g. `voice: {outgoing: {application_sid: AP…}, incoming: {allow: true}}`, `video: {room}`, `chat: {service_sid}`, `data_sync: {service_sid}`. Default TTL 3600s, max 24h. Always mint server-side with the SDK helper (`AccessToken` + `VoiceGrant` etc.).

**Test credentials** (Console → test Account SID/Auth Token) hit the live API but don't send or charge; they only work on Messages, Calls, IncomingPhoneNumbers (buy) and Lookups, with magic numbers like `+15005550006` (valid From), `+15005550001` (invalid → 21211), `+15005550009` (non-mobile → 21614).

## 3. Request encoding

- `Content-Type: application/x-www-form-urlencoded` (or `multipart/form-data`). Sending JSON to a form endpoint yields params-missing errors (e.g., 21604 "'To' required").
- **URL-encode values**: `+` → `%2B`, spaces → `+`/`%20`, `&` → `%26`. With curl, use `--data-urlencode` per param.
- **Arrays**: repeat the key — `MediaUrl=https://a.jpg&MediaUrl=https://b.jpg`; `StatusCallbackEvent=initiated&StatusCallbackEvent=answered`. (SDKs take lists.)
- **Booleans**: `true` / `false` strings.
- **Nested/dotted params**: some APIs use dot notation — `Timers.Inactive=PT1H`, `MessagingBinding.Address=+1…`, `Bindings.Email.Address`.
- **JSON-in-form**: `Attributes={"tier":"gold"}`, Studio `Parameters={"name":"Ana"}`, `ContentVariables={"1":"Ana"}` — URL-encode the whole JSON string.
- **Inequality filters on list endpoints** are part of the param name: `DateSent>=2026-09-01` → encoded `DateSent%3E%3D=2026-09-01`; `StartTime<`, `DateCreated>`. GET list filters go in the query string.
- **Dates in requests**: 2010 API filters accept `YYYY-MM-DD` (and `DateSent` accepts full ISO timestamps); `SendAt` takes ISO 8601; durations (Conversations timers) are ISO 8601 durations (`PT10M`).
- **Update = POST to the instance URL** with only the fields to change. Empty value (`Body=`) can mean "clear/redact".

## 4. Responses & dates

- 2010 API JSON fields: `sid`, `account_sid`, `date_created` (RFC 2822), `uri` (relative, `.json`), `subresource_uris`.
- Product APIs: ISO 8601 dates, `url` (absolute), `links` object for subresources.
- Money: `price` is a string, often negative (`"-0.00790"`), `price_unit` e.g. `USD`; can be `null` until billing finalizes.
- Many values are `null` until an async event occurs (e.g., `date_sent`, `duration`, `error_code`).

## 5. Pagination

Default page size 50; set `PageSize` up to 1000. **Always follow the URL Twilio gives you** — don't construct page numbers; newer pages use an opaque `PageToken`.

2010 API list:
```json
{ "messages": [...], "page": 0, "page_size": 50,
  "uri": "/2010-04-01/Accounts/AC.../Messages.json?PageSize=50&Page=0",
  "first_page_uri": "...", "next_page_uri": "/2010-04-01/...&Page=1&PageToken=PASM...",
  "previous_page_uri": null }
```
`next_page_uri` is **relative** — prefix `https://api.twilio.com`. Stop when it's `null`.

Product APIs (v1/v2):
```json
{ "services": [...], "meta": { "page": 0, "page_size": 50, "first_page_url": "...",
  "previous_page_url": null, "url": "...", "next_page_url": "https://verify.twilio.com/v2/Services?PageSize=50&Page=1&PageToken=...", "key": "services" } }
```
`meta.key` names the array; `meta.next_page_url` is absolute.

SDKs: `list()` loads everything (with `limit`), `stream()`/`each()` iterates lazily, `page()` gives one page. For big exports use the **Bulk Export** API (`bulkexports.twilio.com/v1`) instead of paging millions of records.

## 6. Errors & status codes

| HTTP | Meaning in Twilio | Action |
|---|---|---|
| 200 | OK (fetch/list/update) | — |
| 201 | Created | Async work may still be pending |
| 202 | Accepted, processing | Poll or wait for callback |
| 204 | Deleted | — |
| 400 | Invalid parameters | Read `code` + `message`; fix request, don't retry |
| 401 | Bad/missing credentials (20003) | Check key/secret, region, stripped headers |
| 403 | Forbidden (permission, trial restriction, compliance) | Fix account setup |
| 404 | Not found (20404) — also returned for **approved/expired Verify** checks and resources in another account/region | Check SID, account, region |
| 405 | Method not allowed | e.g., PUT/PATCH |
| 409 | Conflict (e.g., Studio execution already active for To/From) | Handle/end existing |
| 412 | Precondition failed (ETag mismatch) | Re-read and retry |
| 429 | Too Many Requests (20429) — concurrency limit | Retry with backoff + jitter |
| 500/502/503/504 | Twilio side | Retry with backoff (only idempotent ops blindly — see §8) |

Error body:
```json
{ "code": 21211, "message": "Invalid 'To' Phone Number: +1555...", "more_info": "https://www.twilio.com/docs/errors/21211", "status": 400 }
```
Two kinds of errors: **synchronous** (HTTP 4xx on the API call) and **asynchronous** (the request succeeded, but `error_code` appears later on the resource/status callback — e.g., 30007 carrier filtering). Asynchronous ones also show in the Console **Debugger** and via `monitor.twilio.com/v1/Alerts`. Error codes → `references/error-codes.md`.

## 7. Rate limits, concurrency, retries

- REST API limits are mostly **concurrency-based** per account (in-flight requests), not a published RPS. Watch the `Twilio-Concurrent-Requests` response header; exceed → 429/20429.
- **Product throughput is separate from API limits.** Messages beyond sender throughput are *queued*, not rejected (up to ValidityPeriod, max 36000s/10h, then 30001). Rough guides: US long code ~1 MPS (10DLC throughput depends on brand trust score/campaign), toll-free starts ~3 MPS, short code 100+ MPS. Outbound voice: account **CPS** (calls per second) default 1, raisable.
- Retry policy: exponential backoff with jitter (e.g., 1s, 2s, 4s, 8s, cap ~30s, 5 tries) on 429 and 5xx/timeouts. Don't retry 4xx other than 429/409-when-appropriate.
- Prefer webhooks/status callbacks over polling. If you must poll, poll slowly and stop at terminal states.
- Keep SDKs current (Twilio suggests reviewing quarterly).

## 8. Idempotency & conflicts

- There is **no general idempotency key** on create endpoints. Retrying a `POST /Messages` after a timeout can send a duplicate. Mitigate: short client timeouts are risky — prefer longer timeouts (≥15s) and, on ambiguous failure, look up by your own correlation (e.g., list Messages by `To`, `DateSent>` recent; or store the SID once returned) before resending. For Studio, 409 prevents duplicate active executions per To/From.
- Twilio's own webhook retries include an `I-Twilio-Idempotency-Token` request header — dedupe on it in your handlers.
- **Optimistic concurrency** on TaskRouter Task and Sync List/Map items/Documents: read `ETag`, send `If-Match: <etag>` on update; mismatch → 412.
- Without `If-Match`, last write wins.

## 9. Regions & edges

Twilio Regions (data residency/processing): **US1** (default), **IE1**, **AU1**, plus newer JP1, BR1, DE1, SG1 (availability varies by product — check the regional availability page). Edges are network ingress points: `ashburn`, `dublin`, `frankfurt`, `sydney`, `tokyo`, `singapore`, `sao-paulo`, `umatilla`, etc.

- Hostname pattern: `{product}.{edge}.{region}.twilio.com` — e.g., `api.dublin.ie1.twilio.com`, `api.sydney.au1.twilio.com`. Edge-less forms (`api.ie1.twilio.com`) stopped working 28 Apr 2026.
- **Credentials are per region.** Create API keys in the target region.
- SDKs: set both `region` and `edge` (or `TWILIO_REGION`, `TWILIO_EDGE` env vars). Region without edge routes to US1.
- Data in one region isn't visible from another; a SID created in IE1 404s on US1 hosts.
- Webhook egress edge can be pinned with the `#e=` connection override (see webhooks.md).

## 10. Subaccounts

- `POST /2010-04-01/Accounts.json` with `FriendlyName` creates a subaccount (needs parent Auth Token/Main key). Suspend/close via `Status=suspended|closed` on the account.
- Parent credentials can act on a subaccount by putting the **subaccount SID in the URL** (`/Accounts/{SubSid}/Messages.json`). Product APIs don't carry the SID in the path — use subaccount-specific keys.
- ISVs: one subaccount per end customer isolates numbers, usage, compliance, and suspensions.

## 11. Useful headers

Response: `Twilio-Request-Id` (give to support), `Twilio-Request-Duration`, `Twilio-Concurrent-Requests`, `ETag`.
Request (webhooks from Twilio): `X-Twilio-Signature`, `I-Twilio-Idempotency-Token`, `X-Home-Region`, `User-Agent: TwilioProxy/1.1`.
Request (to Twilio): `X-Twilio-Webhook-Enabled: true` (Conversations — fire webhooks for REST-originated actions), `If-Match`.

## 12. Debugging checklist for a failing call

1. Reproduce with curl (`-v` shows headers). If curl works and the SDK doesn't, it's an SDK/config issue.
2. Host/region right? `.json` on 2010 endpoints? Correct Account SID in path?
3. Credentials: key vs Auth Token, right region, no whitespace, not a Standard key on `/Accounts`.
4. Encoding: form not JSON; `+` encoded; arrays repeated; JSON strings for JSON params.
5. Read `code`/`more_info`; check Console Debugger or `GET https://monitor.twilio.com/v1/Alerts` for async errors.
6. Trial account? (Unverified destinations → 21608/21219; "Sent from your Twilio trial account" prefix.)
7. Compliance: US 10DLC registration (30034), toll-free verification (30032), geo permissions (21408 SMS, 21215 voice).
