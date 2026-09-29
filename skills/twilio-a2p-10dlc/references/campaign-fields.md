# Campaign (use case) information

Source: collect-business-info page + UsAppToPerson resource docs + June 2026 changelog. Verified Sept 2026.

A Campaign describes *what* a brand sends and *how* recipients consented. One brand can have several campaigns (up to 5 without justification). Collect this after the brand is approved — the available use cases depend on brand type and can be listed via `GET /v1/Services/{MG}/Compliance/Usa2p/Usecases?BrandRegistrationSid=BN…`.

The campaign is submitted as a `UsAppToPerson` resource under a Messaging Service. Params below are the form-field names (PascalCase) with the doc's snake_case in parentheses.

## Required fields

| Form param | Rules |
|---|---|
| `BrandRegistrationSid` | `BN…` from brand registration. |
| `Description` (`description`) | 40–4096 chars. Who sends, to whom, why. Must align with the use case. Financial institutions doing first-party lending must say "Direct Lending" here regardless of use case (there is also a `DirectLending` boolean param). |
| `MessageFlow` (`message_flow`) | 40–2049 chars. The consent story. List **every** opt-in method. If a website is used: link to the opt-in page, and mention the privacy policy and T&C URLs. If the opt-in page isn't publicly reachable, host screenshots and link them. TCR reviewers read this first. |
| `MessageSamples` (`message_samples`) | 2–5 samples, 20–1024 chars each. Repeated form key. Each must: name the brand (or its website), match the description and use case, use `[square brackets]` for variables, and include real example links/phone numbers if `HasEmbeddedLinks`/`HasEmbeddedPhone` are true. Include STOP language. |
| `UsAppToPersonUsecase` (`us_app_to_person_usecase`) | See use case tables below. |
| `HasEmbeddedLinks` | boolean. If true, put example URLs in the samples. |
| `HasEmbeddedPhone` | boolean. If true, put the numbers in the samples. |
| `PrivacyPolicyUrl` | **Required since 2026-06-30.** Public HTTPS URL. Missing → error 30933. Content fails review → 30908. |
| `TermsAndConditionsUrl` | **Required since 2026-06-30.** Public HTTPS URL. Missing → error 30934. Content fails review → 30882. |

## Conditionally required (keyword handling)

Only needed when the business manages its own STOP/HELP/START handling instead of using Twilio's default or Advanced Opt-Out. If using Twilio's, these are auto-populated.

| Form param | Rules |
|---|---|
| `OptInMessage` | 20–320 chars. Required if users can text a keyword to subscribe. Include: brand name, confirmation of recurring messages, how to get help, how to opt out. |
| `OptInKeywords` | Comma-delimited, ≤255 chars. Required alongside `OptInMessage`. |
| `OptOutMessage` | 20–320 chars. Must acknowledge the request and confirm no further messages; brand name recommended. |
| `OptOutKeywords` | Comma-delimited alphanumeric, ≤255 chars. |
| `HelpMessage` | 20–320 chars. Brand name + support contact. |
| `HelpKeywords` | Comma-delimited alphanumeric, ≤255 chars. |

Other booleans on the resource: `SubscriberOptIn`, `AgeGated`, `DirectLending`. Check the resource doc for current defaults.

## Use cases

### Standard brand
`2FA`, `ACCOUNT_NOTIFICATION`, `CUSTOMER_CARE`, `DELIVERY_NOTIFICATION`, `FRAUD_ALERT`, `HIGHER_EDUCATION`, `MARKETING`, `MIXED`, `POLLING_VOTING` (not political), `PUBLIC_SERVICE_ANNOUNCEMENT`, `SECURITY_ALERT`.

`MIXED` covers multiple use cases but typically means lower throughput and higher per-message cost — steer customers to a specific use case when one fits.

### Low-Volume Standard brand
`LOW_VOLUME` — multi-use-case, lower monthly fee than MIXED, fixed at the lowest throughput tier.

### Special (extra approval, may get better throughput/fees)
`AGENTS_FRANCHISES`, `CHARITY` (501(c)(3) only, not religious orgs), `K12_EDUCATION`, `PROXY`, `EMERGENCY`, `POLITICAL` (527 / 501(c)(4)(5)(6) only), `SOCIAL`, `SWEEPSTAKE`.

### Sole proprietor
Must be `SOLE_PROPRIETOR`; one campaign per sole-prop brand.

## Privacy policy and T&C acceptance criteria

**Privacy policy passes if it:** is public (no login), states mobile numbers are not shared with third parties, discloses message frequency (e.g. "up to 4 msgs/month"), and includes "Message and data rates may apply".

**Privacy policy fails if it:** is login-gated, lacks the no-sharing statement, or isn't at the URL given.

**T&C passes if it:** is public (no login or download) and lives on the same domain as the business website.

**T&C fails if it:** redirects off-domain, is a PDF behind auth, or isn't public.

## Example that passes review

Description: `Acme Sandwich Co. sends order confirmations and delivery-status updates to customers who placed an order on acmesandwich.com and opted in to SMS at checkout.`

Message flow: `Customers opt in at checkout on https://acmesandwich.com/checkout by entering their mobile number and checking "Text me order updates." They can also text START to (415) 555-0100. Privacy policy: https://acmesandwich.com/privacy. Terms: https://acmesandwich.com/terms. Msg frequency varies. Msg & data rates may apply. Reply STOP to cancel, HELP for help.`

Samples:
- `Acme Sandwich Co: your order #[order_id] is confirmed and will be ready at [time]. Reply STOP to opt out.`
- `Acme Sandwich Co: your order #[order_id] is out for delivery. Track it at https://acmesandwich.com/t/[id]. Reply STOP to opt out.`

Use case: `DELIVERY_NOTIFICATION`, `HasEmbeddedLinks=true`, `HasEmbeddedPhone=false`.
