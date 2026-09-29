# Twilio endpoint reference for Confirm

Every row was checked against `references/twilio-oai/spec/yaml/`. Re-grep before relying on a detail not listed here — the spec is the authority, this file is a map.

Contents: 1. Encoding by API family · 2. Voice & Messaging (2010) · 3. Lookup v2 · 4. Memory v1 · 5. Conversation Orchestrator v2 · 6. Intelligence v2 · 7. TwiML (not in specs) · 8. Grep recipes

## 1. Encoding by API family

| API | Host | Body | Field case |
|---|---|---|---|
| 2010 (`twilio_api_v2010.yaml`) | `api.twilio.com` | `application/x-www-form-urlencoded` | PascalCase (`To`, `StatusCallback`) |
| Lookup v2 | `lookups.twilio.com` | GET query params | PascalCase (`Fields`) |
| Intelligence v2 | `intelligence.twilio.com` | form-encoded on create | PascalCase (`ServiceSid`, `Channel`) |
| Orchestrator v2 | `conversations.twilio.com` | `application/json` | camelCase (`displayName`, `memoryStoreId`) |
| Memory v1 | `memory.twilio.com` | `application/json` | camelCase |

Auth for all: HTTP Basic, Standard API key `SK…` + secret.

## 2. Voice & Messaging — `twilio_api_v2010.yaml`

| Action | Method + path |
|---|---|
| Create call | `POST /2010-04-01/Accounts/{AccountSid}/Calls.json` |
| Fetch / update call (redirect `Url`, `Status=completed`) | `GET` / `POST /2010-04-01/Accounts/{AccountSid}/Calls/{Sid}.json` |
| Call webhook/request log | `GET …/Calls/{CallSid}/Events.json` |
| Send / list messages | `POST` / `GET /2010-04-01/Accounts/{AccountSid}/Messages.json` |
| Fetch message | `GET …/Messages/{Sid}.json` |
| Numbers | `…/IncomingPhoneNumbers.json` |

CreateCall params Confirm uses (verify descriptions with grep):

| Param | Spec meaning / Confirm use |
|---|---|
| `To`, `From` | E.164. `From` = Twilio number. |
| `Url` | TwiML webhook (`{TWILIO_WEBHOOK_URL}/webhooks/voice`). |
| `Twiml` | Inline TwiML, max 4000 chars. **Ignored if `Url` is also sent.** Confirm's fallback when no public URL. |
| `StatusCallback` / `StatusCallbackEvent` | `/webhooks/call-status`; events `initiated ringing answered completed`. |
| `Timeout` | Ring seconds, default 60, max 600. |
| `TimeLimit` | "Maximum duration of the call in seconds." Env `TWILIO_CALL_TIME_LIMIT`. |
| `MachineDetection` | `Enable` or `DetectMessageEnd` (env `TWILIO_MACHINE_DETECTION`). `AnsweredBy` starting `machine` → voicemail drop, no Gather. |

Errors seen in this project: `21219` / `21608` (trial, unverified `To`), `20003` (bad credentials), `11200` (TwiML URL unreachable — tunnel down).

## 3. Lookup — `twilio_lookups_v2.yaml`

`GET https://lookups.twilio.com/v2/PhoneNumbers/{PhoneNumber}?Fields=line_type_intelligence` — URL-encode `+` as `%2B` in the path. Confirm checks line type before SMS (skip SMS to landline).

## 4. Memory — `twilio_memory_v1.yaml` (host `memory.twilio.com`)

| Action | Method + path | Notes |
|---|---|---|
| Create store | `POST /v1/ControlPlane/Stores` | JSON `{"displayName": "confirm-dev", "description": "…"}`; `displayName` required, `^[a-zA-Z0-9-]+$`, ≤64. Max 15 stores/account. **Async: `202`** with `Operation-Id`, `Location`, `Retry-After` headers. |
| Poll operation | `GET /v1/ControlPlane/Operations/{operationId}` | Wait until done; store id looks like `mem_store_…`. |
| List / fetch store | `GET /v1/ControlPlane/Stores`, `/v1/ControlPlane/Stores/{storeId}` | |
| Profiles, Observations, ConversationSummaries | `/v1/Stores/{storeId}/Profiles/…` | Leave extraction off for the first pass. |

## 5. Conversation Orchestrator — `twilio_conversations_v2.yaml` (host `conversations.twilio.com`)

| Action | Method + path |
|---|---|
| Create configuration | `POST /v2/ControlPlane/Configurations` (optional `Idempotency-Key` header, UUID, 24h TTL) |
| Fetch / update configuration | `/v2/ControlPlane/Configurations/{id}` |
| Poll async operation | `GET /v2/ControlPlane/Operations/{id}` |
| List conversations | `GET /v2/Conversations` |
| Communications (SMS body or voice transcript in `content`) | `GET /v2/Conversations/{ConversationId}/Communications` |
| Participants / Actions | `/v2/Conversations/{ConversationId}/Participants`, `/Actions` |

Create-configuration body — required: `displayName` (≤32, `^[a-zA-Z0-9-_ ]+$`), `description`, `conversationGroupingType` (`GROUP_BY_PROFILE` | `GROUP_BY_PARTICIPANT_ADDRESSES` | `GROUP_BY_PARTICIPANT_ADDRESSES_AND_CHANNEL_TYPE`), `memoryStoreId`. Optional: `channelSettings`, `statusCallbacks` (≤20, each needs `url`), `intelligenceConfigurationIds` (≤5), `memoryExtractionEnabled` (default `false`), `conversationsV1Bridge`.

```json
{
  "displayName": "confirm-capture",
  "description": "Observe Confirm reminder calls and SMS",
  "conversationGroupingType": "GROUP_BY_PARTICIPANT_ADDRESSES",
  "memoryStoreId": "mem_store_…",
  "memoryExtractionEnabled": false,
  "channelSettings": {
    "VOICE": { "captureRules": [ { "from": "<TWILIO_PHONE_NUMBER>", "to": "*" },
                                 { "from": "*", "to": "<TWILIO_PHONE_NUMBER>" } ] },
    "SMS":   { "captureRules": [ { "from": "<TWILIO_PHONE_NUMBER>", "to": "*" },
                                 { "from": "*", "to": "<TWILIO_PHONE_NUMBER>" } ] }
  }
}
```
Channel keys must be valid channel types (`VOICE`, `SMS`, `RCS`, `WHATSAPP`, `CHAT`); each capture rule requires `from` and `to` (`*` wildcard). Fill numbers from env at runtime — never hardcode.

Behavior (docs, not spec): Orchestrator observes traffic; voice capture transcribes (fees + AI addendum). The quickstart's inbound test differs from Confirm's outbound calls, but capture still works when the Twilio number is in the VOICE rules. Not HIPAA/PCI eligible per product docs — check before using with PHI.

## 6. Conversational Intelligence — `twilio_intelligence_v2.yaml` (host `intelligence.twilio.com`)

| Action | Method + path |
|---|---|
| Services (PII redaction settings live here) | `/v2/Services`, `/v2/Services/{Sid}` |
| Attach operator to service | `/v2/Services/{ServiceSid}/Operators/{OperatorSid}` |
| Operators: pre-built / custom / types | `/v2/Operators/PreBuilt`, `/v2/Operators/Custom`, `/v2/OperatorTypes` |
| Create transcript | `POST /v2/Transcripts` (form-encoded; required `ServiceSid`, `Channel`) |
| Results | `GET /v2/Transcripts/{TranscriptSid}/OperatorResults`, `/Sentences` |

Use post-call only (extract, classify, generate). Not for live DTMF or in-call decisions. v3 exists in `twilio_intelligence_v3.yaml` — check before mixing versions.

## 7. TwiML (not in the OpenAPI specs — cite TwiML docs)

```xml
<Response>
  <Gather numDigits="1" action="/webhooks/voice/gather" method="POST">
    <Say voice="Polly.Joanna" loop="0">Press 1 to confirm, 2 to reschedule.</Say>
  </Gather>
  <Say>We didn't get that.</Say>
</Response>
```
- No input → falls through to verbs after `</Gather>`.
- Speech: `input="speech"` or `"speech dtmf"`, `speechTimeout="auto"` or integer, `hints="confirm, reschedule"`; action receives `SpeechResult`, `Confidence`. `partialResultCallback` receives `UnstableSpeechResult` for streaming partials.
- Respond `Content-Type: text/xml`. Validate `X-Twilio-Signature` with the Auth Token against the public URL.

## 8. Grep recipes

```bash
S=references/twilio-oai/spec/yaml
grep -n "^  /" $S/twilio_memory_v1.yaml                         # all paths in a spec
grep -n -A8 "^                MachineDetection:" $S/twilio_api_v2010.yaml
grep -n -B2 -A10 "operationId: CreateConfiguration" $S/twilio_conversations_v2.yaml
grep -n -A12 "conversations.v2.capture_rule:" $S/twilio_conversations_v2.yaml
grep -n -A10 "^    ServiceRequest:" $S/twilio_memory_v1.yaml
```
