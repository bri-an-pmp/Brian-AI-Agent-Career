# Programmable Messaging (SMS, MMS, WhatsApp, RCS)

Contents: 1. Message resource · 2. Status lifecycle · 3. Messaging Services · 4. Segments & encoding · 5. Scheduling, link shortening, validity · 6. Inbound & TwiML · 7. WhatsApp & Content API · 8. Compliance (10DLC, toll-free, short code, opt-out) · 9. Throughput · 10. Gotchas

---

## 1. Message resource

`https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json`

| Op | HTTP |
|---|---|
| Create/send | `POST …/Messages.json` |
| Fetch | `GET …/Messages/{SM…}.json` |
| List | `GET …/Messages.json?To=…&From=…&DateSent>=…&DateSent<=…&PageSize=…` |
| Update (redact / cancel) | `POST …/Messages/{Sid}.json` with `Body=` (redact) or `Status=canceled` (scheduled only) |
| Delete | `DELETE …/Messages/{Sid}.json` (204) |
| Media list/fetch/delete | `…/Messages/{Sid}/Media.json`, `…/Media/{ME…}` |

**Create — required:** `To` + one sender (`From` **or** `MessagingServiceSid`) + one content (`Body`, `MediaUrl`, or `ContentSid`). (`Body` and `MediaUrl` may be combined for MMS.)

Key optional params:
- `StatusCallback` — URL for delivery status events (or set on the Messaging Service).
- `MediaUrl` (repeat up to 10; public URLs; 5 MB total for MMS typical; WhatsApp up to 16 MB per media) · `SendAsMms=true`.
- `ContentSid` (`HX…`) + `ContentVariables` (JSON string) — Content API templates (required for WhatsApp outside 24h window).
- `ScheduleType=fixed` + `SendAt` (ISO 8601, 15 min–35 days ahead) — needs `MessagingServiceSid`.
- `ValidityPeriod` (1–36000 s; default 36000) — drop if still queued after this.
- `ShortenUrls=true` — needs Messaging Service with a verified link-shortening domain.
- `SmartEncoded=true` — swap smart quotes/dashes etc. for GSM-7 equivalents (saves segments).
- `MaxPrice`, `ProvideFeedback`, `Attempt`, `ForceDelivery`, `PersistentAction` (geo/mailto/tel actions for some channels), `RiskCheck=disable` (opt out of SMS-pumping checks on eligible OTP traffic), `ApplicationSid`.

Response highlights: `sid`, `status`, `num_segments`, `num_media`, `price` (null until billed), `error_code`/`error_message`, `direction` (`outbound-api`, `outbound-reply`, `inbound`, `outbound-call`), `messaging_service_sid`, `date_sent`.

List filters: `To`, `From`, `DateSent`, `DateSent<`, `DateSent>`. Filter keys with operators must be URL-encoded (`DateSent%3E=2026-09-01`).

## 2. Status lifecycle

Outbound: `accepted` (Messaging Service picking a sender) / `scheduled` → `queued` → `sending` → `sent` (carrier accepted) → `delivered` (carrier DLR positive) | `undelivered` (DLR negative) | `failed` (never left Twilio) → `read` (WhatsApp/RCS only). `canceled` for canceled scheduled messages. Inbound: `receiving` → `received`.

- `sent` without later `delivered` is normal for carriers/countries that don't return DLRs.
- `failed`/`undelivered` carry `ErrorCode` (see error-codes.md; 30003–30008, 30034, 30032, 21610…).
- Callbacks are not ordered; rank states rather than trusting arrival order.

## 3. Messaging Services (`MG…`)

`https://messaging.twilio.com/v1/Services` — a container for senders + config. Use one for anything beyond a toy: it's required for scheduling, link shortening, A2P 10DLC campaigns, sender pools, sticky sender, geo-match, and fallback.

- Create: `POST /v1/Services` `FriendlyName=…`; configure `InboundRequestUrl`, `InboundMethod`, `FallbackUrl`, `StatusCallback`, `StickySender`, `SmartEncoding`, `MmsConverter`, `AreaCodeGeomatch`, `FallbackToLongCode`, `ValidityPeriod`, `ScanMessageContent`, `UseInboundWebhookOnNumber`, `Usecase`.
- Sender pool: `POST /v1/Services/{MG}/PhoneNumbers` `PhoneNumberSid=PN…`; `/ShortCodes` `ShortCodeSid=SC…`; `/AlphaSenders` `AlphaSender=ACME`; WhatsApp/RCS senders via Channel Senders.
- **Inbound precedence:** if `UseInboundWebhookOnNumber=false` (default), the Service's inbound setting wins over the number's `SmsUrl`. A common "my webhook isn't firing" cause.
- Deleting a Service releases its senders back to the account (doesn't release numbers).

## 4. Segments & encoding

- GSM-7: 160 chars single / 153 per segment when concatenated. UCS-2 (any non-GSM char — emoji, many accented letters, smart quotes): 70 / 67. One stray `’` flips the whole message to UCS-2 and can double cost.
- `Body` max 1600 chars (21617 if exceeded); Twilio recommends ≤ 320 chars for deliverability.
- You're billed per segment, inbound and outbound. `num_segments` tells you after the fact; compute beforehand if cost matters.

## 5. Scheduling, link shortening, validity

- Schedule: `MessagingServiceSid`, `ScheduleType=fixed`, `SendAt=2026-10-01T15:00:00Z` → status `scheduled`. Cancel: `POST …/Messages/{SM}.json` `Status=canceled`.
- Link shortening + click tracking: verified domain on the Service, `ShortenUrls=true`; click events via the Service's click callback.
- `ValidityPeriod` protects time-sensitive content (OTPs) from being delivered late.

## 6. Inbound & TwiML

Configure `SmsUrl` on the number (`IncomingPhoneNumbers`) or `InboundRequestUrl` on the Service. Twilio POSTs form params (see webhooks.md §2). Reply with TwiML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>Thanks! We got your message.</Message>
  <!-- or: <Message to="+1..." from="+1..." action="/status"><Body>Hi</Body><Media>https://…/a.jpg</Media></Message> -->
</Response>
```
Verbs: `<Message>` (attrs: `to`, `from`, `action`, `method`; nouns `<Body>`, `<Media>`), `<Redirect>`. Empty `<Response/>` = no reply. You can also ignore TwiML and reply via the REST API asynchronously (better if your processing is slow).

## 7. WhatsApp & Content API

- Addresses: `To=whatsapp:+14155552671`, `From=whatsapp:+1…` (or a Messaging Service containing the WhatsApp sender).
- **24-hour customer service window**: freeform messages allowed only within 24h of the user's last inbound message. Outside it, send an **approved template** via `ContentSid` + `ContentVariables`. Sending `Body` outside the window → **63016** (since Apr 2025, template-text-in-Body is rejected too).
- Sandbox for testing (users join with a code); production needs a WhatsApp sender tied to a Meta Business Manager/WABA (one WABA per Twilio account; limits apply).
- Read receipts: status `read` / `EventType=READ` in callbacks.

**Content API** (`https://content.twilio.com/v1/Content`) — JSON body, not form:
```bash
curl -X POST https://content.twilio.com/v1/Content \
  -u "$TWILIO_API_KEY:$TWILIO_API_SECRET" -H "Content-Type: application/json" \
  -d '{"friendly_name":"order_update","language":"en","variables":{"1":"Ana","2":"#123"},
       "types":{"twilio/text":{"body":"Hi {{1}}, order {{2}} shipped."}}}'
```
Types: `twilio/text`, `twilio/media`, `twilio/quick-reply`, `twilio/call-to-action`, `twilio/list-picker`, `twilio/card`, `twilio/carousel`, `twilio/catalog`, `whatsapp/card`, `whatsapp/authentication`, … One template can carry several types; Twilio picks per channel (SMS falls back to text).
WhatsApp approval: `POST /v1/Content/{HX}/ApprovalRequests/whatsapp` JSON `{"name":"order_update","category":"UTILITY"}` (`UTILITY|MARKETING|AUTHENTICATION`); check with `GET /v1/Content/{HX}/ApprovalRequests`.
Send: `ContentSid=HX…&ContentVariables={"1":"Ana","2":"#123"}` on `POST /Messages`.

RCS: sent via a Messaging Service with an RCS sender; falls back to SMS when the device isn't RCS-capable. Use Content API rich types.

## 8. Compliance

- **US A2P 10DLC** (local long codes → US): brand + campaign registration via Trust Hub/Messaging APIs; unregistered traffic fails with **30034**. → use the `twilio-a2p-10dlc` skill for the full flow.
- **Toll-free verification**: unverified toll-free numbers can't send SMS to US/CA (**30032**). `POST https://messaging.twilio.com/v1/Tollfree/Verifications` with `TollfreePhoneNumberSid`, `BusinessName`, `BusinessWebsite`, `NotificationEmail`, `UseCaseCategories`, `UseCaseSummary`, `ProductionMessageSample`, `OptInType` (`VERBAL|WEB_FORM|PAPER_FORM|VIA_TEXT|MOBILE_QR_CODE|IMPORT`), `OptInImageUrls`, `MessageVolume`, business address/contact fields, and `BusinessRegistrationNumber` (+ authority/country) unless sole prop. Statuses `PENDING_REVIEW → IN_REVIEW → TWILIO_APPROVED | TWILIO_REJECTED` (editable if `edit_allowed`). Webhook via `ExternalReferenceId`/status callback.
- **Short codes**: applied for via Console; carrier approval takes weeks.
- **Opt-out**: Twilio auto-handles STOP/UNSUBSCRIBE/… on long codes & toll-free (Advanced Opt-Out on Messaging Services lets you customize keywords/responses). Sending to an opted-out recipient → **21610**. Respect opt-outs in your own DB too.
- **Geo permissions**: Console → Messaging → Geo permissions; blocked destination → **21408**.
- International sender rules vary (alphanumeric sender IDs, pre-registration in many countries) — check the country's guidelines page.
- **SMS pumping / fraud**: enable SMS Pumping Protection (Verify Fraud Guard for OTP), geo-permission lockdown, and Lookup `sms_pumping_risk`.

## 9. Throughput

Queueing is per sender. Rough starting points: US 10DLC depends on campaign/brand trust (T-Mobile daily caps; per-carrier MPS), toll-free ~3 MPS (raisable), short code ~100 MPS, international long codes often 1–10 MPS. Messages over capacity queue up to `ValidityPeriod` (≤10h), then fail with **30001**. Scale with a Messaging Service sender pool or higher-throughput sender types. The API itself is concurrency-limited (429/20429) separately.

## 10. Gotchas

- `+` not URL-encoded → `To= 1555…` → 21211.
- Trial accounts: only verified destination numbers; body prefixed "Sent from your Twilio trial account".
- 21606: `From` isn't an SMS-capable Twilio number on *this* account (check subaccount/region).
- 21612: To/From combination unsupported (e.g., US toll-free to some international, short code to non-US).
- 21614: `To` is a landline (for SMS).
- `sent` ≠ `delivered`; 30007 = carrier filtering (content/registration); 30003/30005/30006 = handset/number issues.
- Redacting `Body` doesn't delete; `DELETE` removes the record (billing data retained).
- Store `MessageSid` from the create response; use it to correlate callbacks.
