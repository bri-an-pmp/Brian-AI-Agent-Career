# Troubleshooting A2P 10DLC

Timelines and fees change; search `twilio.com/docs/messaging/compliance/a2p-10dlc/troubleshooting-a2p-brands` (append `.md`) and the pricing help-center article before quoting numbers. Everything below is the durable diagnostic logic.

## Where to look

| Layer | Fetch | Field(s) |
|---|---|---|
| Customer Profile / TrustProduct | `GET trusthub.twilio.com/v1/CustomerProfiles/{BU}` | `status`: draft, pending-review, in-review, twilio-rejected, twilio-approved; `errors[]` |
| Policy dry-run | `POST …/{BU}/Evaluations` | `status` compliant/noncompliant, `results[].invalid[]` with `error_code` (22214–22219 family = missing/mismatched requirement) |
| Brand | `GET messaging.twilio.com/v1/a2p/BrandRegistrations/{BN}` | `status`, `identity_status`, `brand_score`, `failure_reason`, `brand_feedback[]` |
| Campaign | `GET messaging.twilio.com/v1/Services/{MG}/Compliance/Usa2p/{QE}` | `campaign_status`, `failure_reason`, `errors[]` |
| Live traffic | Message resource `error_code` | 30034 = unregistered/unmatched 10DLC number; 30007 = carrier filtering |

## Brand failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `FAILED`, tax ID / name mismatch | `business_name` doesn't match IRS records; used W-9 name; EIN < 90 days old | Re-enter name exactly from CP 575 / 147c (every line above the address). For a new EIN, wait a few weeks. Urgent: send the federal EIN letter to Twilio Support for a manual identity appeal (~5–7 business days, fee applies). |
| `FAILED`, website | Site unreachable, parked, login-walled, or redirects to another brand | Fix the site or provide the right domain; resubmit. |
| `FAILED`, email/address reuse | Rep email or street already used ~10× across TCR (any vendor) | Use a different corporate email / address. |
| `UNVERIFIED` identity, low `brand_score` | Standard brand with thin public footprint | Optional: request manual secondary vetting (fee) to raise score → higher throughput tier. |
| Sole prop stuck | OTP not answered within 24 h, mobile is a VoIP/CPaaS number, or mobile used > 3× | Use a real personal US/CA mobile; restart. |
| Public company suspended | Authentication+ 2FA email to `brand_contact_email` never completed | Use a corporate mailbox (not free-mail, not a distribution list) and complete the link. |
| Sole prop registered but should have been Standard | Business has an EIN | Delete/re-register as Low-Volume or Standard; sole-prop registration will incur fees and block sending. |

Failed brands can usually be edited and resubmitted (fee may apply). Deleting and recreating is a last resort.

## Campaign failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Error 30933 / 30934 on create | Missing `PrivacyPolicyUrl` / `TermsAndConditionsUrl` (required since 2026-06-30) | Add both as top-level form params. |
| Error 30908 / 30882 | Privacy policy / T&C content failed review | Privacy: public, "we do not share mobile numbers", frequency, "msg & data rates may apply". T&C: public, same domain, not a gated PDF. |
| `FAILED`, opt-in unclear | `MessageFlow` doesn't describe a concrete consent step, or opt-in page isn't public | Rewrite: where, how, what they agree to; link the page; host screenshots if gated. |
| `FAILED`, samples don't match | Samples say "marketing" but use case is `ACCOUNT_NOTIFICATION`; brand not named in samples; links claimed but none in samples | Align samples ↔ description ↔ use case; name the brand in every sample; include real links/numbers. |
| `FAILED`, wrong use case | Picked a use case the brand isn't eligible for | `GET …/Usa2p/Usecases?BrandRegistrationSid=` and pick from the list. Use case itself can't be edited — delete and recreate (new vetting fee). |
| `FAILED`, prohibited content | SHAFT (sex, hate, alcohol, firearms, tobacco), gambling, lending without disclosure, third-party lead gen, debt collection without proper framing | Some are outright banned; others need age gating (`AgeGated`), `DirectLending`, or special use cases. |
| `SUSPENDED` | Carrier/TCR complaint or brand 2FA lapse | Check `errors[]`, contact Support. |
| > 5 campaigns rejected | Per-brand cap without justification | Consolidate, or provide a business reason to Twilio. |

Text fields (description, flow, samples, opt-in/out/help) on a `FAILED` campaign can be edited via Console or API and resubmitted; the use case cannot.

## Traffic failures after approval

- **30034** — number sent from isn't in a Messaging Service with a `VERIFIED` campaign, or the campaign/brand was suspended. Attach the number to the right service; send with `MessagingServiceSid`.
- **30007** — carrier filtered content despite registration. Usually URL shorteners on shared domains, all-caps, or content drifting from the registered samples.
- **Throughput** — MPS is set by brand `identity_status`/score and use case, and per-carrier daily caps apply (T-Mobile enforces a daily segment cap per brand). Queueing beyond MPS is normal; use Messaging Service queueing and `ScheduleType` where appropriate.

## Timelines (verify before quoting)

Sole-prop brands: minutes. Standard brands: minutes to hours for identity check; secondary vetting longer. Campaigns: sole-prop fast; standard campaigns several business days to a couple of weeks depending on TCR backlog. Don't promise a date — recommend registering before development is finished.

## What to say to the customer

Registration is a launch dependency, not a launch-day task. The two things that most often stall it are (1) legal name/EIN not matching IRS records and (2) a privacy policy without the mobile-number non-sharing statement. Fix those on day one.
