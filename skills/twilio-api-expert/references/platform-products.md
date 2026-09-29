# Other Twilio Products (Conversations, Studio, Serverless, TaskRouter, Sync, Video, Event Streams, SendGrid, Numbers, Usage, Accounts)

Contents: 1. Conversations (classic v1) · 2. Conversations v2 / Orchestrator · 3. Studio · 4. Functions & Assets (Serverless) · 5. TaskRouter · 6. Sync · 7. Video · 8. Event Streams · 9. SendGrid email · 10. Phone Numbers & regulatory · 11. Usage, billing, monitoring · 12. Flex (pointer)

---

## 1. Conversations (classic) — `https://conversations.twilio.com/v1`

Multi-party threads spanning chat (SDK), SMS, MMS, WhatsApp, Messenger, GBM. Docs now at `/docs/conversations-classic`.

Hierarchy: `Services (IS…)` → `Conversations (CH…)` → `Participants (MB…)`, `Messages (IM…)`, `Webhooks`; plus `Users`, `Roles`, `Credentials` (push), `Configuration`, `Configuration/Addresses` (auto-create conversations on inbound SMS/WhatsApp). Top-level `/v1/Conversations` uses the default service.

- Create: `POST /v1/Conversations` `FriendlyName`, `UniqueName`, `Attributes` (JSON string), `MessagingServiceSid`, `State` (`active|inactive|closed`), `Timers.Inactive=PT1H`, `Timers.Closed=P1D` (min 1m / 10m).
- Add SMS participant: `POST /v1/Conversations/{CH}/Participants` `MessagingBinding.Address=+1555…` & `MessagingBinding.ProxyAddress=+1<your Twilio number>`. WhatsApp: prefix both with `whatsapp:`. Chat user: `Identity=alice`. Group MMS: `MessagingBinding.ProjectedAddress`.
- Send: `POST /v1/Conversations/{CH}/Messages` `Author`, `Body`, `Attributes`, `MediaSid` (upload to MCS first), `ContentSid`/`ContentVariables`.
- Pitfall: 50416-type error when a participant's address+proxy pair already belongs to another active conversation — close/reuse the existing conversation.
- **Webhooks**: pre-action (`onMessageAdd`, `onConversationAdd`, `onParticipantAdd`, …) can **modify** (return 200 + JSON with `body`/`author`/`attributes`/`friendly_name`) or **reject** (return 4xx/5xx); post-action (`onMessageAdded`, `onConversationStateUpdated`, `onDeliveryUpdated`, …) are notifications. 5s timeout; no response = proceed. Configure globally (`/v1/Configuration/Webhooks`), per service (`/v1/Services/{IS}/Configuration/Webhooks`), or per conversation (`/v1/Conversations/{CH}/Webhooks`, post-action only; targets `webhook`, `studio`, `trigger`).
- REST-originated actions don't fire webhooks unless you send header `X-Twilio-Webhook-Enabled: true`.
- Chat clients use an Access Token with ChatGrant(`service_sid`).

## 2. Conversations v2 / Conversation Orchestrator

Newer API at `conversations.twilio.com` (v2) with resources Configuration, Conversation, Participant (types `CUSTOMER`, `HUMAN_AGENT`, `AI_AGENT`, …), Communication, Action, Operation. Webhooks are JSON `{eventType, timestamp, data}`. Only available in the new Twilio Console; not HIPAA/PCI eligible. Ask which version the user is on before giving code — the models differ. Fetch `https://www.twilio.com/docs/api/conversations/v2` (append `.md`) for exact endpoints.

## 3. Studio — `https://studio.twilio.com/v2`

Visual flows (`FW…`) triggered by incoming call, message, or REST API.
- Trigger via REST: `POST /v2/Flows/{FW}/Executions` `To`, `From` (Twilio number or MG), `Parameters` (JSON string → `{{flow.data.x}}`). Returns `FN…`. **409** if an execution is already active for that To/From — end it (`POST /v2/Flows/{FW}/Executions/{FN}` `Status=ended`) or wait.
- Inspect: `/Executions/{FN}/Context` (JSON of all widget variables), `/Executions/{FN}/Steps`.
- Flow CRUD: `POST /v2/Flows` with `FriendlyName`, `Status=draft|published`, `Definition` (JSON) — enables CI/CD of flows; `/v2/Flows/{FW}/Revisions`; `POST /v2/Flows/Validate`.
- Inside flows: `{{trigger.message.Body}}`, `{{widgets.<name>.parsed.<field>}}` (HTTP widget JSON), `{{contact.channel.address}}`.
- Hook a number to a flow by setting `SmsUrl`/`VoiceUrl` to `https://webhooks.twilio.com/v1/Accounts/{AC}/Flows/{FW}` (Console does this).

## 4. Functions & Assets (Serverless) — `https://serverless.twilio.com/v1`

Node.js functions hosted at `https://{service}-{random}-{env}.twil.io/{path}`.

```js
exports.handler = async (context, event, callback) => {
  const client = context.getTwilioClient();          // pre-authenticated SDK
  const twiml = new Twilio.twiml.MessagingResponse();
  twiml.message(`You said: ${event.Body}`);           // event = merged query+body params
  return callback(null, twiml);                       // TwiML → text/xml automatically
  // JSON/custom: const r = new Twilio.Response(); r.setStatusCode(200); r.appendHeader('Content-Type','application/json'); r.setBody({ok:true}); callback(null, r);
};
```
- `context` has env vars (`context.MY_KEY`), `DOMAIN_NAME`, `PATH`, `SERVICE_SID`, `ENVIRONMENT_SID`; `event.request.headers`/`cookies`.
- Visibility: **public** (anyone), **protected** (requires valid `X-Twilio-Signature` — use for webhooks), **private** (only `require(Runtime.getFunctions()[…].path)` from other functions).
- Limits: ~10s execution timeout, request/response size limits, concurrency caps — keep functions short; offload long work.
- Deploy: Console editor, or Twilio CLI `twilio serverless:deploy` (serverless toolkit). API resources: Services (`ZS`), Environments (`ZE`), Functions (`ZH`)/Versions, Assets, Builds (`ZB`), Deployments, Variables, Logs.
- Assets: static files (audio for `<Play>`, images for MMS) — public/protected/private.

## 5. TaskRouter — `https://taskrouter.twilio.com/v1`

Skills-based routing engine (powers Flex). `Workspaces (WS)` → `Workers (WK)` with `Attributes` JSON (skills), `Activities (WA)` (Available/Offline/…, `Available=true|false`), `TaskQueues (WQ)` with `TargetWorkers` expression (`skills HAS "spanish"`), `Workflows (WW)` with `Configuration` JSON (filters → targets, priority, timeout, escalation), `Tasks (WT)` with `Attributes` JSON, `Reservations (WR)`, `TaskChannels`, `Events`, `Statistics` (cumulative/real-time).

- Create task: `POST /v1/Workspaces/{WS}/Tasks` `WorkflowSid`, `Attributes={"type":"support","language":"es"}`, `Priority`, `Timeout`, `TaskChannel`. Or from voice: `<Enqueue workflowSid="WW…"><Task>{"language":"es"}</Task></Enqueue>`.
- **Assignment callback** (`AssignmentCallbackUrl` on Workflow): Twilio POSTs the reservation; respond `200` with JSON instruction: `{"instruction":"accept"}`, `{"instruction":"reject"}`, `{"instruction":"dequeue","from":"+1…","post_work_activity_sid":"WA…"}`, `{"instruction":"call","url":"…","from":"…"}`, `{"instruction":"conference",…}`, `{"instruction":"redirect","call_sid":"…","url":"…"}` — or empty 200 and handle via REST (`POST …/Tasks/{WT}/Reservations/{WR}` `ReservationStatus=accepted` / `Instruction=conference`).
- Reservation statuses: `pending`, `accepted`, `rejected`, `timeout`, `canceled`, `rescinded`, `wrapping`, `completed`.
- Task lifecycle: `pending` → `reserved` → `assigned` → `wrapping` → `completed` (or `canceled`). Task updates support `If-Match`/ETag.
- `EventCallbackUrl` on the Workspace delivers all events (`task.created`, `reservation.accepted`, `worker.activity.update`, …).

## 6. Sync — `https://sync.twilio.com/v1`

Real-time state for web/mobile via Sync SDK. Service (`IS…`) → **Documents** (single JSON object, ~16 KB), **Lists** (ordered items), **Maps** (keyed items), **Message Streams** (pub/sub, ~4 KB messages, not persisted). `Ttl` on objects for auto-expiry. Updates to Documents/List/Map items accept `If-Match`. Clients use Access Token + SyncGrant(`service_sid`). Webhooks per service (`WebhookUrl`, `ReachabilityWebhooksEnabled`). Rate limits per object (~20 updates/s) — shard hot objects.

## 7. Video — `https://video.twilio.com/v1`

- Rooms: `POST /v1/Rooms` `UniqueName`, `Type=group` (recommended; `group-small`, `peer-to-peer`, `go` legacy), `MaxParticipants`, `RecordParticipantsOnConnect`, `StatusCallback`, `EmptyRoomTimeout`/`UnusedRoomTimeout` (min), `MaxParticipantDuration`, `AudioOnly`. End: `POST /v1/Rooms/{RM}` `Status=completed`.
- Clients join with Access Token + VideoGrant(`room`); rooms can also be created on first join (ad-hoc).
- Recordings per track (`/v1/Recordings`, `RT…`) → combine with **Compositions** (`POST /v1/Compositions` `RoomSid`, `VideoLayout` JSON, `AudioSources`, `Format=mp4|webm`). Recording Rules (`/v1/Rooms/{RM}/RecordingRules`) to start/stop per track.
- Status callbacks: `room-created`, `participant-connected`, `track-added`, `room-ended`, `recording-completed`, …
- Video's 2023 EOL announcement was reversed; it remains a supported product.

## 8. Event Streams — `https://events.twilio.com/v1`

Push Twilio events (message status, call summaries, Verify, TaskRouter, Studio, Conversations, …) to one place.
- `POST /v1/Sinks` `Description`, `SinkType=webhook|kinesis|segment`, `SinkConfiguration` (JSON: `{"destination":"https://…","method":"POST","batch_events":true}` or Kinesis `arn`, `role_arn`, `external_id`). Validate: `POST /v1/Sinks/{DG}/Test` then `/Validate` with the test id you received.
- `POST /v1/Subscriptions` `SinkSid`, `Description`, `Types=[{"type":"com.twilio.messaging.message.delivered","schema_version":1}, …]` (repeat `Types` param with JSON strings). Browse `GET /v1/Types` and `/v1/Schemas/{id}`.
- Payloads are **CloudEvents** JSON; webhook sinks are signed with `X-Twilio-Signature` (JSON body → `bodySHA256` style). **At-least-once**, retried up to 4 hours, may be out of order — dedupe on event `id`.

## 9. SendGrid (email) — `https://api.sendgrid.com/v3`

Different auth and encoding from core Twilio: `Authorization: Bearer SG.xxxxx` (SendGrid API key, separate account), JSON bodies.
```bash
curl -X POST https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer $SENDGRID_API_KEY" -H "Content-Type: application/json" \
  -d '{"personalizations":[{"to":[{"email":"ana@example.com"}],"dynamic_template_data":{"name":"Ana"}}],
       "from":{"email":"no-reply@acme.com"},"template_id":"d-xxxxxxxx"}'
```
→ `202 Accepted`, empty body, `X-Message-Id` header. Max 1000 personalizations/request, ~30 MB total, `send_at` ≤ 72h ahead. EU data residency host `api.eu.sendgrid.com` (EU subuser). Sender must be a verified single sender or authenticated domain (SPF/DKIM). Event Webhook (delivered/open/click/bounce, JSON array POSTs, optional ECDSA signature in `X-Twilio-Email-Event-Webhook-Signature`), Inbound Parse (multipart form). Rate limits via `X-RateLimit-*` headers; 429 → back off.

## 10. Phone Numbers & regulatory

- Search: `GET /2010-04-01/Accounts/{AC}/AvailablePhoneNumbers/{ISO}/{Local|TollFree|Mobile}.json?AreaCode=415&Contains=555&SmsEnabled=true&VoiceEnabled=true&InRegion=CA&PageSize=20`.
- Buy: `POST …/IncomingPhoneNumbers.json` `PhoneNumber=+1…` (or `AreaCode`), plus `AddressSid`/`BundleSid` where regulations require.
- Configure: `POST …/IncomingPhoneNumbers/{PN}.json` `SmsUrl`, `SmsMethod`, `SmsFallbackUrl`, `VoiceUrl`, `VoiceMethod`, `VoiceFallbackUrl`, `StatusCallback`, `VoiceApplicationSid`/`SmsApplicationSid` (TwiML App), `TrunkSid`, `EmergencyAddressSid`, `FriendlyName`, `VoiceReceiveMode=voice|fax`.
- Release: `DELETE …/IncomingPhoneNumbers/{PN}.json` (irreversible after the grace period).
- Move numbers between subaccounts: `POST …/Accounts/{OldAC}/IncomingPhoneNumbers/{PN}.json` `AccountSid={NewAC}` (parent credentials).
- Regulatory bundles & addresses: `numbers.twilio.com/v2/RegulatoryCompliance/Bundles`, `/2010-04-01/Accounts/{AC}/Addresses.json`. Hosted SMS / porting: `numbers.twilio.com/v1/Porting…`, `HostedNumberOrders`.
- Outgoing caller IDs: `POST …/OutgoingCallerIds.json` to verify a non-Twilio number for use as `From` in calls.
- Trust Hub (`trusthub.twilio.com/v1`): CustomerProfiles, TrustProducts, EndUsers, SupportingDocuments — for A2P 10DLC, SHAKEN/STIR, CNAM, branded calling. → `twilio-a2p-10dlc` skill.

## 11. Usage, billing, monitoring

- Usage: `GET /2010-04-01/Accounts/{AC}/Usage/Records[/Daily|/Monthly|/Yearly|/Today|/Yesterday|/ThisMonth|/LastMonth|/AllTime].json?Category=sms&StartDate=2026-09-01&EndDate=2026-09-30&IncludeSubaccounts=true`.
- Usage Triggers: `POST …/Usage/Triggers.json` `UsageCategory=totalprice`, `TriggerValue=100`, `Recurring=daily|monthly|yearly|alltime`, `CallbackUrl` — spend alerts / kill switches.
- Balance: `GET …/Accounts/{AC}/Balance.json`. Pricing: `pricing.twilio.com/v2/Messaging/Countries/{ISO}`, `/v2/Voice/Numbers/{E164}`.
- Monitor: `GET https://monitor.twilio.com/v1/Alerts?StartDate=…&LogLevel=error` (Debugger errors/warnings), `/v1/Events` (audit log of Console/API changes). Console Debugger webhook for real-time alert delivery.
- Bulk Export: `bulkexports.twilio.com/v1/Exports/Messages/Days` for daily message logs.

## 12. Flex (pointer)

Flex = contact center on TaskRouter + Conversations + Voice. APIs: `flex-api.twilio.com/v1` (Configuration, FlexFlows, Interactions API for omnichannel tasks, Plugins API for plugin versions/releases, Insights). UI customization via React plugins (Flex Plugins CLI). For deep Flex UI work, fetch the Flex developer docs.
