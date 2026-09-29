# Verify v2 & Lookup v2

## Verify v2 — `https://verify.twilio.com/v2`

Use Verify for OTP instead of hand-rolling codes over Messages: Twilio generates/stores/expires codes, handles channel fallback, localization, rate limiting, fraud (Fraud Guard, geo-permissions), and doesn't require you to register 10DLC for OTP traffic on its own senders in most cases.

### 1. Create a Service (once)
```bash
curl -X POST https://verify.twilio.com/v2/Services \
  -u "$TWILIO_API_KEY:$TWILIO_API_SECRET" \
  --data-urlencode "FriendlyName=Acme"
```
→ `VA…`. Options: `CodeLength` (integer 4–10 — set it explicitly, e.g., 6, rather than relying on the default), `LookupEnabled`, `SkipSmsToLandlines`, `DtmfInputRequired`, `TtsName`, `Psd2Enabled`, `CustomCodeEnabled`, `DoNotShareWarningEnabled`, `DefaultTemplateSid`, push/TOTP/WhatsApp/passkey configs.

### 2. Start a verification
`POST /v2/Services/{VA}/Verifications` — `To` (E.164 or email), `Channel` = `sms|call|whatsapp|email|sna|auto` (plus `totp`/`push` via Factors). Optional `Locale`, `CustomFriendlyName`, `CustomCode` (if enabled), `TemplateSid`, `ChannelConfiguration` (JSON; e.g., email template substitutions), `RateLimits` (JSON for Programmable Rate Limits), `AppHash` (Android SMS Retriever), `DeviceIp`, `RiskCheck`.
→ `201` `{"sid":"VE…","status":"pending","channel":"sms","send_code_attempts":[…],"valid":false}`.

### 3. Check the code
`POST /v2/Services/{VA}/VerificationCheck` — `To` (or `VerificationSid`) + `Code`.
→ `200` `{"status":"approved","valid":true}` or `{"status":"pending","valid":false}` for a wrong code.
- **404 (20404) on check** means no pending verification: already approved, expired (10 min), canceled, or max attempts. Handle it as "request a new code", not a server error.
- 5 check attempts max per verification (60202); 5 send attempts per 10 min per `To` by default (60203).

### Statuses
`pending`, `approved`, `canceled` (`POST /Verifications/{VE}` `Status=canceled`), `max_attempts_reached`, `deleted`, `failed`, `expired`. Approved/expired verifications can't be fetched (404) — log the SID and status yourself.

### Other Verify features
- **Fraud Guard** (SMS-pumping protection, on by default): blocked attempts → 60410 (12h prefix block).
- **Programmable Rate Limits**: `/Services/{VA}/RateLimits` + `/Buckets`, then pass `RateLimits={"end_user_ip":"1.2.3.4"}` (JSON string) on create; exceeding a bucket rejects the send with a rate-limit error.
- **Silent Network Auth** (`Channel=sna`): carrier-based, no code; returns an `sna.url` the device must open over cellular data.
- **Push & TOTP**: `/Services/{VA}/Entities/{identity}/Factors` (create factor, verify with `AuthPayload`), `/Challenges`.
- **Passkeys** (WebAuthn) support in newer Verify versions.
- **Email channel**: needs a SendGrid-backed Mailer config on the Service.
- **Events**: Verify events via Event Streams; attempts via `GET /v2/Attempts` (Verification Attempts logs, filter by date/channel/country).
- Common errors: 60200 invalid parameter (bad `To`/`Channel`), 60202 max check attempts, 60203 max send attempts, 60205 SMS not supported to landline (use `call`), 60410 Fraud Guard, 60223 channel disabled, 20404 check against non-pending verification.

## Lookup v2 — `https://lookups.twilio.com/v2/PhoneNumbers/{PhoneNumber}`

`GET` only. Basic lookup (free) validates and formats:
```bash
curl -G "https://lookups.twilio.com/v2/PhoneNumbers/%2B14159929960" \
  -u "$TWILIO_API_KEY:$TWILIO_API_SECRET" \
  --data-urlencode "Fields=line_type_intelligence,sms_pumping_risk"
```
URL-encode the `+` as `%2B` in the path (or pass national format with `CountryCode=US`).

Response: `valid`, `validation_errors` (`TOO_SHORT`, `TOO_LONG`, `INVALID_BUT_POSSIBLE`, `INVALID_COUNTRY_CODE`, `INVALID_LENGTH`, `NOT_A_NUMBER`), `phone_number` (E.164), `national_format`, `country_code`, `calling_country_code`, plus one object per requested field.

`Fields` (comma-separated; all but `validation` are paid):
- `line_type_intelligence` → `type`: `mobile`, `landline`, `fixedVoip`, `nonFixedVoip`, `personal`, `tollFree`, `premium`, `sharedCost`, `uan`, `voicemail`, `pager`, `unknown`; `carrier_name`, `mobile_country_code`, `mobile_network_code`.
- `caller_name` (US CNAM), `sim_swap` (last SIM change), `call_forwarding`, `line_status` (active/inactive), `identity_match` (compare name/address/DOB; pass `FirstName`, `LastName`, `AddressLine1`, `PostalCode`, `DateOfBirth`…), `reassigned_number` (US, pass `LastVerifiedDate`), `sms_pumping_risk` (score 0–100 + `sms_pumping_risk_score`, `carrier_risk_category`), `phone_number_quality_score`, `pre_fill`.
- Availability varies by country and some fields need approval (identity_match, sim_swap).

Patterns: validate at signup (basic, free) → route SMS vs voice by `line_type_intelligence` → risk-score with `sms_pumping_risk` before sending OTP. Lookup v1 (`/v1/PhoneNumbers?Type=carrier`) is legacy — migrate.
