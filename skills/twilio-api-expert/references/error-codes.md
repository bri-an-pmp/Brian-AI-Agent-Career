# Twilio Error Codes — field guide

Always confirm details at `https://www.twilio.com/docs/api/errors/{code}` (append `.md` for Markdown). Codes appear in the API error body (`code`), on resources (`error_code`), in callbacks (`ErrorCode`), and in the Console Debugger / `monitor.twilio.com/v1/Alerts`.

Ranges: 1xxxx general/TwiML/webhook fetch · 2xxxx REST API & account · 3xxxx messaging delivery · 3100x–3199x Voice SDK/client · 4xxxx TaskRouter · 5xxxx Conversations/Sync/Chat · 6xxxx Verify/Authy · 63xxx channels (WhatsApp, Messenger) · 8xxxx Studio/Serverless · 9xxxx various (OAuth 97xxx).

## Auth & API
| Code | Meaning | Fix |
|---|---|---|
| 20003 | Permission denied / authenticate | Wrong SID/secret pair, whitespace, key from another region, Standard key on `/Accounts`, deleted key, suspended account, proxy stripped `Authorization` |
| 20404 | Resource not found | Wrong SID/account/subaccount/region; Verify check with no pending verification |
| 20429 | Too many requests | Concurrency limit — backoff + jitter |
| 20008 | Test credentials can't access this resource | Use live creds |
| 21604 / 21602 | 'To' / 'Body' required | Usually JSON sent instead of form-encoding |

## Messaging — synchronous (API rejects)
| Code | Meaning |
|---|---|
| 21211 | Invalid 'To' number (often unencoded `+`) |
| 21212 | Invalid 'From' number |
| 21408 | Permission to send to this region not enabled (geo permissions) |
| 21606 | 'From' isn't a valid message-capable Twilio number on this account |
| 21608 | Trial / no approved Primary Compliance Profile → can't send to unverified numbers |
| 21610 | Recipient has opted out (STOP) |
| 21612 | To/From combination can't be routed |
| 21614 | 'To' isn't a mobile number |
| 21617 | Body exceeds 1600 characters |
| 21620 | Invalid media URL(s) |

## Messaging — asynchronous (status `failed`/`undelivered`)
| Code | Meaning | Typical action |
|---|---|---|
| 30001 | Queue overflow (exceeded sender throughput; queued > ValidityPeriod) | More senders / higher-throughput sender, pace sends |
| 30002 | Account suspended | Contact support |
| 30003 | Unreachable destination handset (off, out of coverage) | Retry later |
| 30004 | Message blocked (recipient blocks, carrier block, or blocklist) | Don't retry blindly |
| 30005 | Unknown destination handset (number doesn't exist) | Clean list; Lookup |
| 30006 | Landline or unreachable carrier | Use voice; Lookup line type |
| 30007 | Carrier filtering / violation (spam-like content, unregistered traffic) | Fix content, register (10DLC/TFV), avoid URL shorteners |
| 30008 | Unknown error from carrier | Retry; open ticket if persistent |
| 30032 | Toll-free number not verified | Submit Toll-Free Verification |
| 30034 | US A2P 10DLC — message from unregistered number | Register brand+campaign, attach number to campaign's Messaging Service |

## Webhooks & TwiML
| Code | Meaning |
|---|---|
| 11200 | HTTP retrieval failure (non-2xx, timeout) |
| 11205 | HTTP connection failure |
| 11206 | HTTP protocol violation |
| 11210 | HTTP bad host name (DNS) |
| 11237 | Certificate invalid (self-signed/expired) |
| 11750 | TwiML response body too large (>64 kB) |
| 12100 | Document parse failure (invalid XML) |
| 12200 | Schema validation warning (unknown verb/attr) |
| 12300 | Invalid Content-Type |
| 15003 | Warning: your callback URL returned 4xx/5xx (return 200 TwiML or 204) |

## Voice
| Code | Meaning |
|---|---|
| 13223 / 13224 | Invalid / unsupported dial number |
| 13225 | Call blocked by Twilio (fraud risk, regulation, or no approved Primary Customer Profile for +1 calls) |
| 13227 | Geo permission not permitting call (<Dial>) |
| 21205 | Invalid URL |
| 21210 / 21212 | 'From' not a verified/owned number |
| 21215 | Geo permission blocks this call destination |
| 21219 | Trial: 'To' not verified |
| 31000–31999 | Voice SDK / client errors (e.g., 31005 connection error, 31204 invalid JWT, 31205 JWT expired) |
| 32xxx | SIP / trunking errors |

## Verify
| Code | Meaning |
|---|---|
| 60200 | Invalid parameter (To/Channel) |
| 60202 | Max check attempts reached |
| 60203 | Max send attempts reached |
| 60205 | SMS not supported to landline — use `call` |
| 60223 | Delivery channel disabled on the Service |
| 60410 | Fraud Guard blocked (12h prefix block) |
| 20404 | Check against approved/expired/non-existent verification |

## WhatsApp / channels
| Code | Meaning |
|---|---|
| 63016 | Outside 24h window — send an approved template via `ContentSid` |
| 63018 | Rate limit exceeded for channel (WhatsApp default ~80 MPS, RCS 100 MPS, or per-recipient frequency) |
| 63024 | Invalid recipient (not on WhatsApp, hasn't accepted ToS, outdated client) |
| 63032 | Recipient is in a Meta experiment — can't deliver; skip them |
| 63049 | Meta blocked marketing template (US recipients can't receive WhatsApp marketing since Apr 1 2025; engagement limits elsewhere) |

When a code isn't listed, fetch its page instead of guessing — Twilio has 1,500+ codes and wording changes.
