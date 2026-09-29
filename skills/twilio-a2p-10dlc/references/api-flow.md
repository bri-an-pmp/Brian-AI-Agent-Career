# A2P 10DLC via the REST API — the flow, at the HTTP level

This is the ISV Standard/Low-Volume flow (direct customers use the Console, but the resources are identical under the hood). Verified against the ISV onboarding guide, Sept 2026. Sole-prop differences are at the end.

## What every call has in common

| Layer | Detail |
|---|---|
| Hosts | Trust Hub: `https://trusthub.twilio.com/v1`. Messaging: `https://messaging.twilio.com/v1`. Core (Addresses): `https://api.twilio.com/2010-04-01/Accounts/{AccountSid}`. |
| Auth | HTTP Basic. Username = Account SID (or API Key SID), password = Auth Token (or API Key Secret). curl: `-u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN`. The SDK sets `Authorization: Basic base64(sid:token)` for you. |
| Request body | `Content-Type: application/x-www-form-urlencoded`. Param names are PascalCase (`FriendlyName`). Nested data (`Attributes`) is a **JSON string inside a single form field**. Arrays (`MessageSamples`) are the **same key repeated**. |
| Response | JSON, snake_case. Create → `201 Created`. Fetch/update → `200`. Delete → `204 No Content`. |
| Errors | `400` validation (body has `code`, `message`, `more_info`), `401` bad auth, `404` wrong SID/path, `429` rate limited. |
| "Update" | Twilio has no PUT/PATCH; updates are `POST` to the resource URL with only the changed fields. |
| Idempotency | None. A retried create makes a second resource. Save SIDs as you go. |

Node SDK pattern for everything below:

```js
const twilio = require("twilio");
const client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
```

## Prerequisite (Console, once)

The ISV's **Primary Customer Profile** must be `twilio-approved`, business type "ISV Reseller or Partner". Note its SID (`BU…`). Use the Account SID of the account the customer will send from (subaccount if you use them).

## Step 1 — Secondary Customer Profile (the customer's identity)

### 1.1 Create the profile → `BU…`

```
POST https://trusthub.twilio.com/v1/CustomerProfiles
PolicySid=RNdfbf3fae0e1107f8aded0e7cead80bf5   (fixed: secondary profile policy)
FriendlyName=Acme, Inc. Secondary Customer Profile
Email=<ISV's own ops mailbox, NOT the customer's>
StatusCallback=https://isv.example.com/trusthub/status   (optional, recommended)
```

```js
const profile = await client.trusthub.v1.customerProfiles.create({
  policySid: "RNdfbf3fae0e1107f8aded0e7cead80bf5",
  friendlyName: "Acme, Inc. Secondary Customer Profile",
  email: process.env.ISV_OPS_EMAIL,
  statusCallback: "https://isv.example.com/trusthub/status",
});
```

Response `status` starts as `draft`.

### 1.2 Business info EndUser → `IT…`

```
POST https://trusthub.twilio.com/v1/EndUsers
Type=customer_profile_business_information
FriendlyName=Acme, Inc. business info
Attributes={"business_name":"ACME INC","business_type":"Corporation", ...}
```

```bash
ATTRS='{"business_name":"ACME INC","business_type":"Corporation","business_industry":"RETAIL","business_registration_identifier":"EIN","business_registration_number":"12-3456789","business_identity":"direct_customer","business_regions_of_operation":"USA_AND_CANADA","website_url":"https://www.acme.example"}'
curl -X POST https://trusthub.twilio.com/v1/EndUsers \
  --data-urlencode "Type=customer_profile_business_information" \
  --data-urlencode "FriendlyName=Acme, Inc. business info" \
  --data-urlencode "Attributes=$ATTRS" \
  -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN
```

Note what curl is doing: the whole JSON object becomes one percent-encoded form value. The SDK's `attributes: {...}` does `JSON.stringify` for you.

### 1.3 Attach it → `BV…`

```
POST https://trusthub.twilio.com/v1/CustomerProfiles/{BU}/EntityAssignments
ObjectSid=IT…
```

```js
await client.trusthub.v1.customerProfiles(profile.sid)
  .customerProfilesEntityAssignments.create({ objectSid: bizInfo.sid });
```

### 1.4 / 1.5 Authorized rep EndUser → attach

Same as 1.2/1.3 with `Type=authorized_representative_1` and attributes `first_name, last_name, business_title, job_position, phone_number, email`. Optionally repeat with `authorized_representative_2`.

### 1.6 Address → `AD…`

Note the different host — Addresses are a core API resource.

```
POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Addresses.json
CustomerName=ACME INC
Street=1234 Market St
City=San Francisco
Region=CA
PostalCode=94103
IsoCountry=US
FriendlyName=Acme mailing address
```

```js
const address = await client.addresses.create({ customerName: "ACME INC", street: "1234 Market St", city: "San Francisco", region: "CA", postalCode: "94103", isoCountry: "US", friendlyName: "Acme mailing address" });
```

### 1.7 / 1.8 SupportingDocument wraps the address → attach → `RD…`

```
POST https://trusthub.twilio.com/v1/SupportingDocuments
Type=customer_profile_address
FriendlyName=Acme address doc
Attributes={"address_sids":"AD…"}
```

then `POST /CustomerProfiles/{BU}/EntityAssignments` with `ObjectSid=RD…`.

### 1.9 Link to the ISV's Primary profile

`POST /CustomerProfiles/{secondary BU}/EntityAssignments` with `ObjectSid=<primary BU>`. Yes — a profile SID as the object.

### 1.10 Evaluate (dry-run against the policy) → `EL…`

```
POST https://trusthub.twilio.com/v1/CustomerProfiles/{BU}/Evaluations
PolicySid=RNdfbf3fae0e1107f8aded0e7cead80bf5
```

Response `status` is `compliant` or `noncompliant`; `results[]` lists each requirement with `passed`, `failure_reason`, `error_code`, and per-field `invalid[]`. This is the cheapest debugging tool in the whole flow — run it before submitting.

### 1.11 Submit for review

```
POST https://trusthub.twilio.com/v1/CustomerProfiles/{BU}
Status=pending-review
```

(An "update" is a POST to the resource URL.) You can proceed to Step 2 without waiting for `approved`.

## Step 2 — TrustProduct (the A2P compliance bundle)

| # | Call |
|---|---|
| 2.1 | `POST /v1/TrustProducts` with `PolicySid=RNb0d4771c2c98518d916a3d4cd70a8f8b`, `FriendlyName`, `Email` (ISV's), optional `StatusCallback` → `BU…` (yes, same prefix as profiles). |
| 2.2 | `POST /v1/EndUsers` with `Type=us_a2p_messaging_profile_information`, `Attributes={"company_type":"private"}` (add `stock_exchange`,`stock_ticker` only if `public`; `brand_contact_email` for public for-profit — this triggers the Authentication+ 2FA email). |
| 2.3 | `POST /v1/TrustProducts/{BU}/EntityAssignments` `ObjectSid=IT…` |
| 2.4 | `POST /v1/TrustProducts/{BU}/EntityAssignments` `ObjectSid=<secondary CustomerProfile BU>` |
| 2.5 | `POST /v1/TrustProducts/{BU}/Evaluations` `PolicySid=RNb0d4771c2c98518d916a3d4cd70a8f8b` → check `compliant` |
| 2.6 | `POST /v1/TrustProducts/{BU}` `Status=pending-review` |

## Step 3 — Brand registration (submit to TCR) → `BN…`

```
POST https://messaging.twilio.com/v1/a2p/BrandRegistrations
CustomerProfileBundleSid=<secondary CustomerProfile BU>
A2PProfileBundleSid=<TrustProduct BU>
SkipAutomaticSecVet=true        (only for Low-Volume / 527 / Campaign Verify)
Mock=true                        (dev only: fake registration, no fee)
```

```js
const brand = await client.messaging.v1.brandRegistrations.create({
  customerProfileBundleSid: profile.sid,
  a2PProfileBundleSid: trustProduct.sid,
  skipAutomaticSecVet: false,
});
```

Response fields to watch: `status` (`PENDING` → `APPROVED` | `FAILED` | `IN_REVIEW`), `identity_status` (`SELF_DECLARED`, `UNVERIFIED`, `VERIFIED`, `VETTED_VERIFIED`), `brand_score`, `failure_reason`, `tcr_id`. Poll with `GET /v1/a2p/BrandRegistrations/{BN}` or subscribe via Event Streams. Fees are charged on submission; see troubleshooting for what to do on `FAILED`.

## Step 4 — Messaging Service → `MG…`

```
POST https://messaging.twilio.com/v1/Services
FriendlyName=Acme order updates
InboundRequestUrl=https://isv.example.com/sms/inbound   (inbound webhook: Twilio POSTs incoming messages here; reply with TwiML)
```

```js
const service = await client.messaging.v1.services.create({ friendlyName: "Acme order updates", inboundRequestUrl: "https://isv.example.com/sms/inbound" });
```

One campaign attaches to one Messaging Service; all numbers in that service inherit the campaign.

## Step 5 — Campaign (UsAppToPerson) → `QE…`

First, optionally list what use cases this brand may pick:

```
GET https://messaging.twilio.com/v1/Services/{MG}/Compliance/Usa2p/Usecases?BrandRegistrationSid=BN…
```

Then create. Do not do this until brand `status=APPROVED`.

```
POST https://messaging.twilio.com/v1/Services/{MG}/Compliance/Usa2p
BrandRegistrationSid=BN…
UsAppToPersonUsecase=DELIVERY_NOTIFICATION
Description=<40–4096 chars>
MessageFlow=<40–2049 chars>
MessageSamples=<sample 1>
MessageSamples=<sample 2>          ← repeated key = array
HasEmbeddedLinks=true
HasEmbeddedPhone=false
PrivacyPolicyUrl=https://www.acme.example/privacy      ← required since 2026-06-30
TermsAndConditionsUrl=https://www.acme.example/terms   ← required since 2026-06-30
OptInMessage=... OptInKeywords=... OptOutMessage=... OptOutKeywords=... HelpMessage=... HelpKeywords=...   (only if self-managing keywords)
```

```js
const campaign = await client.messaging.v1.services(service.sid).usAppToPerson.create({
  brandRegistrationSid: brand.sid,
  usAppToPersonUsecase: "DELIVERY_NOTIFICATION",
  description: "Acme Sandwich Co. sends order confirmations and delivery-status updates to customers who opted in at checkout on acmesandwich.com.",
  messageFlow: "Customers opt in at https://acmesandwich.com/checkout by entering their mobile number and checking 'Text me order updates'. Privacy: https://acmesandwich.com/privacy. Terms: https://acmesandwich.com/terms. Msg&data rates may apply. Reply STOP to cancel, HELP for help.",
  messageSamples: [
    "Acme Sandwich Co: your order #[order_id] is confirmed and will be ready at [time]. Reply STOP to opt out.",
    "Acme Sandwich Co: your order #[order_id] is out for delivery. Track: https://acmesandwich.com/t/[id]. Reply STOP to opt out.",
  ],
  hasEmbeddedLinks: true,
  hasEmbeddedPhone: false,
  privacyPolicyUrl: "https://acmesandwich.com/privacy",
  termsAndConditionsUrl: "https://acmesandwich.com/terms",
});
```

```bash
curl -X POST "https://messaging.twilio.com/v1/Services/$MG/Compliance/Usa2p" \
  --data-urlencode "BrandRegistrationSid=$BN" \
  --data-urlencode "UsAppToPersonUsecase=DELIVERY_NOTIFICATION" \
  --data-urlencode "Description=Acme Sandwich Co. sends order confirmations and delivery-status updates to customers who opted in at checkout on acmesandwich.com." \
  --data-urlencode "MessageFlow=Customers opt in at https://acmesandwich.com/checkout by entering their mobile number and checking 'Text me order updates'. Privacy: https://acmesandwich.com/privacy. Terms: https://acmesandwich.com/terms. Msg&data rates may apply. Reply STOP to cancel, HELP for help." \
  --data-urlencode "MessageSamples=Acme Sandwich Co: your order #[order_id] is confirmed and will be ready at [time]. Reply STOP to opt out." \
  --data-urlencode "MessageSamples=Acme Sandwich Co: your order #[order_id] is out for delivery. Track: https://acmesandwich.com/t/[id]. Reply STOP to opt out." \
  --data-urlencode "HasEmbeddedLinks=true" \
  --data-urlencode "HasEmbeddedPhone=false" \
  --data-urlencode "PrivacyPolicyUrl=https://acmesandwich.com/privacy" \
  --data-urlencode "TermsAndConditionsUrl=https://acmesandwich.com/terms" \
  -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN
```

Response: `campaign_status` `IN_PROGRESS` → `VERIFIED` | `FAILED` | `SUSPENDED`. Poll `GET /v1/Services/{MG}/Compliance/Usa2p/{QE}` or use Event Streams.

## Step 6 — Attach a 10DLC number to the service

```
POST https://messaging.twilio.com/v1/Services/{MG}/PhoneNumbers
PhoneNumberSid=PN…
```

```js
await client.messaging.v1.services(service.sid).phoneNumbers.create({ phoneNumberSid: "PN…" });
```

Send with `MessagingServiceSid=MG…` instead of `From=` on `POST /2010-04-01/Accounts/{AC}/Messages.json` so Twilio picks a registered number from the pool.

## Async status: the inbound side

Everything above is outbound. Two inbound mechanisms exist:

- **`StatusCallback`** on CustomerProfile / TrustProduct: Twilio POSTs form-encoded status changes to your URL. Validate `X-Twilio-Signature`.
- **Event Streams**: subscribe to brand, campaign, and 10DLC number status events (`com.twilio.messaging.compliance.*`) and sink them to a webhook or Kinesis. Recommended over polling for ISVs with many customers.

## Sole proprietor differences

Same shape, different policies and types: the CustomerProfile uses the sole-prop policy, the EndUser type is `sole_proprietor_information` (brand_name, first/last name, email, mobile_phone_number, vertical), the TrustProduct uses the sole-prop A2P policy, and `BrandRegistrations` is called with `BrandType=SOLE_PROPRIETOR`. Twilio texts an OTP to `mobile_phone_number`; the proprietor must reply within 24 h or the brand fails. One campaign (`SOLE_PROPRIETOR` use case), one number. The sole-prop policy SIDs differ from the standard ones above — fetch `https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/onboarding-isv-api-sole-prop-new.md` for the current values rather than reusing the standard SIDs.

## SID prefixes cheat sheet

`AC` account · `BU` CustomerProfile *and* TrustProduct · `IT` EndUser · `RD` SupportingDocument · `AD` Address · `BV` entity assignment · `EL` evaluation · `RN` policy · `BN` brand · `MG` messaging service · `QE` campaign · `PN` phone number
