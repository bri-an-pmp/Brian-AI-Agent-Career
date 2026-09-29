# Business information to collect (Brand registration)

Source: https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/collect-business-info (last verified Sept 2026 — refetch the `.md` version if anything below is contested).

Parameter names are given in `snake_case` because that's how they appear inside the `Attributes` JSON of Trust Hub `EndUser` resources. In the Console the same fields appear as form labels. Direct (non-ISV) customers should use the Console; ISVs use the API.

## Trust Hub concepts

- **Primary Customer Profile** — the Twilio account holder's own business identity. Must be `twilio-approved` before anything else. ISVs select business type "ISV Reseller or Partner".
- **Secondary Customer Profile** — an ISV's *customer's* business identity (`CustomerProfile` resource, policy `RNdfbf3fae0e1107f8aded0e7cead80bf5`). Direct customers don't create one.
- **TrustProduct** — the A2P-specific compliance container (policy `RNb0d4771c2c98518d916a3d4cd70a8f8b`). Holds the `us_a2p_messaging_profile_information` EndUser and links to the Customer Profile.
- **EndUser** — a typed bag of attributes. Types used here: `customer_profile_business_information`, `authorized_representative_1` (and optional `_2`), `us_a2p_messaging_profile_information`. Sole-prop flow uses `sole_proprietor_information`.
- **SupportingDocument** of type `customer_profile_address` wraps an `Address` (AD…) resource.

## Decide the brand type first

| Brand type | Who | Key signal |
|---|---|---|
| Sole Proprietor | US/CA individual with **no** EIN / Canadian Business Number | hobbyist, freelancer, student; personal name is the brand |
| Low-Volume Standard | Registered business, < ~2,000 segments/day on T-Mobile (verify current cap) | wants lower fees, accepts lowest throughput; set `skip_automatic_sec_vet=true` |
| Standard | Registered business, higher volume | goes through automatic secondary vetting for a trust score |

A sole proprietorship that *has* an EIN must register as Low-Volume or Standard. Registering it as Sole Proprietor incurs fees and blocks sending.

## Sole Proprietor Brand — fields

For sole props the "authorized representative" *is* the proprietor.

| Field | Notes |
|---|---|
| `brand_name` | Usually first + last name; DBA accepted. Hobbyists use personal name. |
| `first_name`, `last_name` | The proprietor. |
| `mobile_phone_number` | E.164. Receives the OTP. Must be a real US/CA mobile, **not** a CPaaS/Twilio number. Max **3** uses across all TCR brand registrations (any vendor). |
| `email` | Valid domain, not disposable. Max **10** uses across TCR. |
| `customer_name` | Business name for the mailing address. |
| `street`, `street_secondary` (opt), `city`, `region` (2-letter), `postal_code`, `iso_country` | Mailing address. Street reused max **10** times across TCR. |
| `vertical` (opt) | One of: AGRICULTURE, COMMUNICATION, ENERGY, ENTERTAINMENT, FINANCIAL, GAMBLING, GOVERNMENT, HEALTHCARE, HOSPITALITY, HUMAN_RESOURCES, INSURANCE, LEGAL, MANUFACTURING, NGO, POLITICAL, POSTAL, PROFESSIONAL, REAL_ESTATE, RETAIL, TECHNOLOGY, TRANSPORTATION |

## Standard / Low-Volume Standard Brand — fields

### Business identity (`customer_profile_business_information` EndUser)

| Field | Rules / allowed values |
|---|---|
| `business_name` | **Exact legal name as on the IRS CP 575 EIN confirmation letter** (or a 147c letter if CP 575 is lost). Not the W-2/W-9 name. If the name spans multiple lines on the letter, include every line above the address line. |
| `business_type` | `Co-operative`, `Corporation`, `Limited Liability Corporation`, `Non-profit Corporation`, `Partnership`. Government orgs use `Non-profit Corporation`. |
| `business_industry` | AGRICULTURE, AUTOMOTIVE, BANKING, CONSTRUCTION, CONSUMER, EDUCATION, ELECTRONICS, ENGINEERING, ENERGY, FAST_MOVING_CONSUMER_GOODS, FINANCIAL, FINTECH, FOOD_AND_BEVERAGE, GOVERNMENT, HEALTHCARE, HOSPITALITY, INSURANCE, JEWELRY, LEGAL, MANUFACTURING, MEDIA, NOT_FOR_PROFIT, OIL_AND_GAS, ONLINE, PROFESSIONAL_SERVICES, RAW_MATERIALS, REAL_ESTATE, RELIGION, RETAIL, TECHNOLOGY, TELECOMMUNICATIONS, TRANSPORTATION, TRAVEL. Government → `GOVERNMENT`; non-profit → `NOT_FOR_PROFIT`. |
| `business_registration_identifier` | `EIN` (US), `DUNS` (US), `CBN` (Canada), `CN` (GB), `ACN` (Australia), `CIN` (India), `VAT` (Estonia), `VATRN` (Romania), `RN` (Israel), `Other`. **Use `EIN` for any US entity or international tax ID; do not use DUNS.** |
| `business_registration_number` | Format follows the identifier: EIN `00-0000000`, DUNS `00-000-0000`, CBN first 9 digits only. |
| `social_media_profile_urls` (opt) | LinkedIn/Facebook/X etc. |
| `website_url` | Must be live, related to `business_name`, and pass an automated screenshot compliance check. Rejected if: unreachable, parked/for-sale, login-required, or redirects to another brand/domain. |
| `business_identity` | `direct_customer`, `isv_reseller_or_partner`, `unknown`. Non-ISV businesses must be `direct_customer`. |
| `business_regions_of_operation` | AFRICA, ASIA, EUROPE, LATIN_AMERICA, USA_AND_CANADA |

### Authorized representative (`authorized_representative_1` EndUser)

| Field | Rules |
|---|---|
| `first_name`, `last_name` | Real person at the business. |
| `business_title` | Exact job title, free text. |
| `job_position` | `Director`, `GM`, `VP`, `CEO`, `CFO`, `General Counsel`, `Other` |
| `phone_number` | E.164. |
| `email` | Valid domain, not disposable, max 10 uses across TCR. |

A second rep is optional (`authorized_representative_2`, same attributes).

### Mailing address (`Address` resource → `customer_profile_address` SupportingDocument)

`customer_name`, `street`, `street_secondary` (opt), `city`, `region` (2-letter), `postal_code`, `iso_country` (e.g. `US`). Street reused max 10 times across TCR.

### A2P messaging profile (`us_a2p_messaging_profile_information` EndUser)

| Field | Rules |
|---|---|
| `company_type` | `government`, `non-profit`, `private`, `public` |
| `stock_exchange` | Only if `public`. AMEX, AMX, ASX, B3, BME, BSE, FRA, ICEX, JPX, JSE, KRX, LON, NASDAQ, NONE, NYSE, NSE, OMX, OTHER, SEHK, SGX, SSE, STO, SWX, SZSE, TSX, TWSE, VSE |
| `stock_ticker` | Only if `public`, e.g. `TWLO`. Omit both stock fields when not public. |
| `brand_contact_email` | **Public, for-profit brands only.** TCR sends an Authentication+ 2FA email here. Must be a corporate address — personal/free-mail and distribution lists fail. |

### Brand registration flags (on `BrandRegistration`, not an EndUser)

| Field | Rules |
|---|---|
| `skip_automatic_sec_vet` | Default `false`. Set `true` only for Low-Volume Standard registration, 527 political orgs, or Campaign Verify token holders. |

## Discovery checklist to hand a customer

1. IRS CP 575 or 147c letter (federal, not state) — legal name and EIN exactly as printed.
2. Entity type and industry (pick from the enums above; don't let them free-text).
3. Public, working website on the brand's own domain.
4. Public privacy policy + T&C on that same domain (needed for the campaign; see `campaign-fields.md`).
5. Authorized rep: name, title, corporate email, phone.
6. Public company? Exchange + ticker + a corporate email that can complete 2FA.
7. Expected daily volume → decides Low-Volume vs Standard.
8. Any prior 10DLC registrations with other vendors (affects the email/address/mobile reuse limits).
