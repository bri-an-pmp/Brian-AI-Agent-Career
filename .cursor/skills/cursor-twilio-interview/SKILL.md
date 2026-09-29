---
name: cursor-twilio-interview
description: Uses Twilio HTTP APIs correctly in this repo by verifying every endpoint and parameter against the twilio-oai OpenAPI YAML, wiring the Confirm Voice/SMS app (Calls, TwiML Gather, status callbacks, webhook HMAC, Lookup v2), and layering Conversation Orchestrator, Memory, Conversational Intelligence, or speech intake without inventing endpoints or replacing Confirm's IVR. Use when the task mentions Twilio, Confirm, POST /Calls, TwiML, Gather, SpeechResult, webhook signatures, Lookup v2, Conversation Orchestrator, Memory stores, Intelligence operators, healthcare voice intake, or edits files under twilio/.
---

# Twilio APIs in this repo (Confirm)

Extends `.cursor/rules/twilio-openapi.mdc` — that rule is the policy; this skill is the workflow. Endpoint tables and request shapes live in [reference.md](reference.md). App how-to: `twilio/README.md`, env knobs: `twilio/.env.example`.

## 1. Always: verify against the spec first

Spec root: `references/twilio-oai/spec/yaml/`

| Product | Spec file |
|---|---|
| Calls, Messages, Incoming Numbers | `twilio_api_v2010.yaml` |
| Lookup | `twilio_lookups_v2.yaml` |
| Messaging services / A2P | `twilio_messaging_v1.yaml` |
| Voice beyond 2010 Calls | `twilio_voice_v1.yaml` (v2/v3 if needed) |
| Conversation Orchestrator | `twilio_conversations_v2.yaml` |
| Memory stores / profiles / observations | `twilio_memory_v1.yaml` |
| Conversational Intelligence | `twilio_intelligence_v2.yaml` (v3 if needed) |

Before claiming a path, method, parameter, default, or enum exists:

```bash
S=references/twilio-oai/spec/yaml
grep -n "^  /" $S/twilio_conversations_v2.yaml          # list paths
grep -n -A6 "^                Timeout:" $S/twilio_api_v2010.yaml   # read a param's description
```

- Cite the filename (and ideally the line) in the answer.
- Do not infer endpoints from the Python SDK, blog posts, or memory. If it is not in the spec, say "not in the spec" and stop.
- TwiML verbs/attributes (`<Gather>`, `<Say>`, `SpeechResult`, `UnstableSpeechResult`) are **not** in the OpenAPI specs — they are TwiML. Cite the Twilio TwiML docs for those and say so.
- Web docs (e.g., Orchestrator quickstart) explain product behavior; the YAML is the REST authority.

## 2. Decision tree — which mechanism?

1. **Place / inspect / hang up a call** → REST, `twilio_api_v2010.yaml` (`POST`/`GET /Calls`).
2. **What the caller hears and presses during the call** → TwiML returned from the `Url` webhook (`<Say>`, `<Gather>`). Not a REST resource.
3. **Free-text answer during the call** → `<Gather input="speech">` (or `speech dtmf`) → `SpeechResult` + `Confidence` on the action webhook.
4. **Record / transcribe / audit what was said across SMS + Voice** → Conversation Orchestrator capture (`twilio_conversations_v2.yaml`) + Memory store (`twilio_memory_v1.yaml`). It **observes** existing traffic; it never places calls, speaks, or collects DTMF.
5. **Structured extraction / classification after hangup** → Intelligence operators on transcripts (`twilio_intelligence_v2.yaml`), attached via `intelligenceConfigurationIds`.
6. **Is this number a mobile before SMS?** → Lookup v2 `Fields=line_type_intelligence` (`twilio_lookups_v2.yaml`).

Never replace Confirm's Gather IVR with Orchestrator. In-call = Gather; after-call = Orchestrator + Intelligence.

## 3. Confirm facts to get right (all verified in `twilio_api_v2010.yaml`)

- Create call: `POST /2010-04-01/Accounts/{AccountSid}/Calls.json` with `To`, `From`, and `Url` and/or `Twiml`. **If both are sent, `Twiml` is ignored** (spec text; `Twiml` max 4000 chars). Confirm sends `Url` so Gather can POST `/webhooks/voice/gather`.
- Inspect: `GET /2010-04-01/Accounts/{AccountSid}/Calls/{Sid}.json`.
- `StatusCallback` + `StatusCallbackEvent` (`initiated`, `ringing`, `answered`, `completed`).
- `Timeout` = seconds to **ring** (default 60, max 600). Too short can miss voicemail.
- `TimeLimit` = "maximum duration of the call in seconds" — Confirm treats it as the cap on connected talk time; not ring time.
- `MachineDetection=DetectMessageEnd` → when `AnsweredBy` starts with `machine`, play a voicemail drop and **skip Gather**.
- `queued` / `ringing` ≠ `completed`. A `201` means Twilio accepted the request, not that anyone answered.
- Twilio must reach a **public HTTPS origin** to fetch TwiML. Without `TWILIO_WEBHOOK_URL`, the app falls back to inline `Twiml` `<Say>` so the phone still rings (no live keypad).
- Current IVR: `<Say>` + `<Gather numDigits="1" action="/webhooks/voice/gather">`; 1 = confirm, 2 = reschedule. `<Say loop="0">` repeats until hangup/`TimeLimit`; barge-in still accepts digits.

## 4. Auth

- REST: Standard API key — `Client(api_key_sid, api_key_secret, account_sid)` (HTTP Basic `SK…:secret`).
- Webhook HMAC (`X-Twilio-Signature`) uses the **Auth Token**. The API key secret is not the webhook secret.
- Validate against the **public** URL Twilio called (tunnel origin), not `http://127.0.0.1:3000`. See `twilio/webhook_verify.py`.
- Orchestrator (`conversations.twilio.com/v2`) and Memory (`memory.twilio.com/v1`) take **JSON bodies with camelCase fields**, unlike the form-encoded PascalCase 2010 API.

## 5. Trial vs full account

- Trial: unverified `To` → `21219` / `21608`. Fix: Console → Verified Caller IDs. Full accounts can dial unverified numbers.
- Trial SMS `From` may not be in inventory → use the dashboard's simulated inbound SMS.

## 6. Repo conventions

- App `twilio/app.py` (Flask dashboard on port 3000), UI `twilio/templates/index.html`, DB `twilio/confirm.db` (`reminders` keyed by callee E.164 = `To` on outbound Voice; `events`).
- Python: use `twilio/.venv`, not system python.
- `load_env()` uses `os.environ.setdefault` → **restart `app.py` after every `.env` change**; stale values otherwise persist.
- Tunnel: `cloudflared tunnel --url http://127.0.0.1:3000`. Quick-tunnel URLs change when the tunnel restarts → update `TWILIO_WEBHOOK_URL`, restart Flask. Never hardcode a tunnel URL in code or docs.
- Local helpers: `POST /api/simulate-dtmf` (localhost only), `GET /api/twiml` (preview), `GET /api/calls/<sid>` (inspect).
- Tests: `twilio/test_api.py --only account` or `--only fetch`. **Never** run or default to `--only call` — it rings a real phone. Ask first.
- Scope: skip Studio, Flex, Media Streams, and recording unless the user explicitly pivots.

## 7. Healthcare speech + AI (designed, not built)

Recommended flow: consent → identity check (known DOB/name/ID) → one spoken question via `<Gather input="speech">` → LLM reviews `SpeechResult` for completeness → read-back and confirm → Orchestrator transcript as audit trail → Intelligence operators post-call → staff queue. AI proposes; the patient or staff confirms.

- Collect on an outbound reminder: confirm/reschedule, high-level visit reason, callback number.
- Do **not** collect unauthenticated: SSN, medication lists, insurance numbers, detailed symptoms.
- No diagnosis or triage. Safety phrases (chest pain, etc.) → transfer or instruct to call emergency services/clinic.
- Requires HIPAA BAA, transcription consent, PII redaction (Intelligence services), no PHI in model logs. Orchestrator voice capture transcribes (fees + Predictive/Generative AI addendum). `memoryExtractionEnabled` defaults to `false` — leave observations/summaries off for a first pass.
- `nexhealth/` (sandbox scheduling) is adjacent and not wired to Confirm.

## 8. Secrets and git

- Never commit `.env`, Auth Token, API key secret, Account SIDs, or personal phone numbers. Don't print tokens or full phone numbers in replies (mask: `+1•••••1234`).
- If a token was pasted into chat, tell the user to rotate it.
- `origin` is the upstream course repo — **do not push** Twilio spikes there. The user's fork is the `mine` remote; confirm before any push.

## 9. Interview lines ("say this")

- "REST creates the Call; Twilio fetches TwiML later from `Url`."
- "Gather is TwiML, not a REST resource."
- "`queued`/`ringing` isn't `completed` — status callbacks tell you what happened."
- "The API key authenticates my requests; the Auth Token signs Twilio's requests to me."
- "Orchestrator observes the conversation; Gather drives it."
