# Programmable Voice & TwiML

Contents: 1. Mental model · 2. Call resource · 3. Call status & callbacks · 4. TwiML verbs cheat-sheet · 5. `<Dial>` · 6. `<Gather>` · 7. Conferences · 8. Recordings · 9. Answering machine detection · 10. Media Streams · 11. ConversationRelay (voice AI) · 12. Client SDKs, TwiML Apps, SIP · 13. Gotchas

---

## 1. Mental model

A call is a state machine driven by **TwiML documents** your server returns. Twilio fetches TwiML on answer (inbound: number's `VoiceUrl`; outbound: `Url`/`Twiml`/`ApplicationSid` on create), executes verbs top-to-bottom, and when a verb has an `action` URL, fetches the next document from there. You can also **interrupt a live call** by `POST`ing new TwiML to the Call resource (`Url` or `Twiml`). When the document runs out, the call hangs up.

## 2. Call resource

`https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Calls.json`

Create (outbound): `POST …/Calls.json` with `To`, `From` (a Twilio number or verified caller ID), and **one of** `Url` | `Twiml` | `ApplicationSid`.

```bash
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Calls.json" \
  -u "$TWILIO_API_KEY:$TWILIO_API_SECRET" \
  --data-urlencode "To=+15558675310" --data-urlencode "From=+15017122661" \
  --data-urlencode "Twiml=<Response><Say>Your appointment is tomorrow at 3.</Say></Response>" \
  --data-urlencode "StatusCallback=https://example.com/call-status" \
  --data-urlencode "StatusCallbackEvent=initiated" --data-urlencode "StatusCallbackEvent=ringing" \
  --data-urlencode "StatusCallbackEvent=answered" --data-urlencode "StatusCallbackEvent=completed"
```
→ `201` with `sid` `CA…`, `status: queued`.

Useful create params: `Method`, `FallbackUrl`, `StatusCallback`/`StatusCallbackMethod`/`StatusCallbackEvent` (repeatable; `completed` is default), `Timeout` (ring seconds, default 60, max 600), `Record`, `RecordingChannels` (`mono|dual`), `RecordingStatusCallback`, `RecordingStatusCallbackEvent`, `MachineDetection` (`Enable|DetectMessageEnd`), `AsyncAmd`, `AsyncAmdStatusCallback`, `MachineDetectionTimeout` (default 30), `SendDigits` (`w` = 0.5s wait, e.g., `ww1234#`), `TimeLimit` (max call length, default 4h), `CallerId` (for Client/SIP), `Trim`, `SipAuthUsername/Password`, `CallToken` (preserve caller ID when forwarding), `CallReason` (branded calling).

Modify a live call — `POST …/Calls/{CA}.json`:
- Redirect: `Url=https://…/new-twiml` or `Twiml=<Response>…</Response>`
- Hang up: `Status=completed` (in-progress) / `Status=canceled` (queued/ringing only)

List: `GET …/Calls.json?To=&From=&Status=&StartTime>=&EndTime<=&ParentCallSid=`. Subresources: `Recordings`, `Notifications`, `Events` (webhook request/response log), `Payments`, `Siprec`, `Streams`, `Transcriptions`, `UserDefinedMessages`.

Account CPS (calls per second) defaults to 1 for API-originated calls; excess calls queue (`queue_time`).

## 3. Call status & callbacks

Statuses: `queued` → `initiated` (event) → `ringing` → `in-progress` → `completed` | `busy` | `no-answer` | `failed` | `canceled`. `direction`: `inbound`, `outbound-api` (REST), `outbound-dial` (child leg from `<Dial>`).

A `<Dial>` creates a **child call** (its own `CA…`, `ParentCallSid` = the original). Billing, status and recordings are per leg.

## 4. TwiML verbs cheat-sheet

| Verb | Purpose | Key attrs |
|---|---|---|
| `<Say>` | TTS | `voice` (e.g., `Polly.Joanna`, `Google.en-US-Neural2-F`, `alice`), `language`, `loop`; supports SSML tags |
| `<Play>` | Play audio URL or DTMF | `loop`, `digits` |
| `<Gather>` | Collect DTMF / speech | see §6 |
| `<Dial>` | Connect to another party | see §5 |
| `<Record>` | Voicemail-style recording | `action`, `maxLength` (3600), `timeout` (5), `finishOnKey`, `playBeep`, `transcribe`, `recordingStatusCallback`, `trim` |
| `<Enqueue>` / `<Leave>` | Put caller in a named queue / leave it | `waitUrl`, `action`, `workflowSid` (TaskRouter) |
| `<Pause>` | Silence | `length` |
| `<Redirect>` | Fetch another TwiML doc | `method` |
| `<Hangup>` / `<Reject>` | End / refuse without billing (`reason=busy|rejected`) | |
| `<Refer>` | SIP REFER transfer | |
| `<Start>` / `<Stop>` | Background: `<Stream>`, `<Siprec>`, `<Transcription>`, `<Recording>` | |
| `<Connect>` | Hand the call to `<Stream>` (bidirectional), `<ConversationRelay>`, `<Room>`, `<VirtualAgent>` | `action` |
| `<Pay>` | PCI-compliant card capture | |
| `<Prompt>`, `<Parameter>` | Nouns inside `<Pay>`, `<Stream>`, `<Client>` etc. | |

Escape `&` as `&amp;` inside TwiML text and URLs. Verbs after a `<Gather action>`/`<Dial action>` that fires are unreachable — control moves to the action URL.

## 5. `<Dial>`

Attrs (defaults): `action` (none), `method` POST, `timeout` 30, `timeLimit` 14400, `callerId` (caller's), `answerOnBridge` false (set **true** so the caller hears real ringback and isn't billed/connected until answered), `record` (`do-not-record|record-from-answer|record-from-ringing|…-dual`), `recordingStatusCallback`, `recordingTrack`, `hangupOnStar`, `ringTone`, `trim`, `sequential` (for multiple `<Number>` nouns), `referUrl`.

Nouns: `<Number>` (attrs `sendDigits`, `url` — whisper TwiML to callee, `statusCallback`/`statusCallbackEvent`, `machineDetection`), `<Client>` (Voice SDK identity; `<Identity>` + `<Parameter>` children), `<Sip>`, `<Conference>`, `<Queue>`, `<Application>`, `<WhatsApp>`. Multiple `<Number>`s ring simultaneously (first to answer wins) unless `sequential="true"`.

Action callback params: `DialCallStatus` (`completed|answered|busy|no-answer|failed|canceled`), `DialCallSid`, `DialCallDuration`, `DialBridged`, `RecordingUrl`. Typical pattern: `<Dial action="/after-dial" timeout="20">` → on `no-answer`/`busy`, return `<Response><Say>…</Say><Record …/></Response>` for voicemail.

## 6. `<Gather>`

Attrs (defaults): `input` `dtmf` (`speech`, `dtmf speech`), `action` (current URL), `method` POST, `timeout` 5, `finishOnKey` `#`, `numDigits` (unlimited), `speechTimeout` (= timeout; `auto` recommended for speech), `speechModel`, `language` en-US, `hints` (≤500 phrases), `profanityFilter` true, `partialResultCallback`, `actionOnEmptyResult` false. Nest `<Say>`, `<Play>`, `<Pause>` for the prompt (barge-in supported).

Action params: `Digits`, `SpeechResult`, `Confidence` (0–1). **No input → falls through to the next verb** after `</Gather>` (so put a retry/`<Redirect>` there), unless `actionOnEmptyResult="true"`.

```xml
<Response>
  <Gather input="dtmf speech" numDigits="1" action="/menu" speechTimeout="auto" hints="sales, support">
    <Say>Press 1 or say sales. Press 2 or say support.</Say>
  </Gather>
  <Redirect>/voice</Redirect>
</Response>
```

## 7. Conferences

TwiML: `<Dial><Conference startConferenceOnEnter="true" endConferenceOnExit="false" waitUrl="…" beep="true" statusCallback="…" statusCallbackEvent="start end join leave mute hold modify speaker announcement" record="record-from-start" maxParticipants="250">RoomName</Conference></Dial>`. The conference exists while participants are in it; name is unique per account while active.

REST: `GET/POST …/Conferences/{CF}.json` (update `Status=completed`, `AnnounceUrl`), Participants: `…/Conferences/{CF or FriendlyName}/Participants.json`:
- Add (dial out into the conference): `POST` with `From`, `To`, `Label`, `EarlyMedia`, `Beep`, `StartConferenceOnEnter`, `EndConferenceOnExit`, `Muted`, `Record`, `StatusCallback(Event)`, `Coaching` + `CallSidToCoach`, `ConferenceStatusCallback`…
- Update: `Muted`, `Hold` + `HoldUrl`, `AnnounceUrl`, `Coaching`.
- Remove: `DELETE`. Participants resource only shows **live** participants — use Voice Insights for history.

Conference is the building block for warm transfer, coaching/whisper/barge, and hold (don't try to "hold" a two-party `<Dial>`).

## 8. Recordings

- Start: `<Record>`, `<Dial record=…>`, `<Conference record=…>`, `<Start><Recording>`, `Record=true` on Calls create, or `POST …/Calls/{CA}/Recordings.json` (params `RecordingChannels`, `RecordingStatusCallback`, `RecordingTrack`).
- Control: `POST …/Calls/{CA}/Recordings/{RE}.json` `Status=paused|in-progress|stopped` (`Twilio.CURRENT` as the RE sid targets the active one). Pause during card capture for PCI.
- Media: `https://api.twilio.com/2010-04-01/Accounts/{AC}/Recordings/{RE}.mp3` (or `.wav`, default); dual-channel `?RequestedChannels=2`. Requires auth if media auth is enforced (recommended). Metadata at `.json`.
- `RecordingStatusCallback`: `RecordingSid`, `RecordingUrl`, `RecordingStatus` (`in-progress|completed|absent|failed`), `RecordingDuration`, `RecordingChannels`, `RecordingSource`.
- Delete: `DELETE …/Recordings/{RE}.json`. Consider external storage + encryption (Recording settings) for compliance.
- Transcription: legacy `<Record transcribe>`; modern: `<Start><Transcription>` real-time or Voice Intelligence (Conversation Intelligence) transcripts.

## 9. Answering machine detection (AMD)

`MachineDetection=Enable` → `AnsweredBy`: `human`, `machine_start`, `fax`, `unknown`. `DetectMessageEnd` waits for the beep → `machine_end_beep|machine_end_silence|machine_end_other`. Use `AsyncAmd=true` + `AsyncAmdStatusCallback` so the call proceeds immediately and you get the result via callback (then redirect the call). Tune `MachineDetectionTimeout`, `MachineDetectionSpeechThreshold`, `MachineDetectionSpeechEndThreshold`, `MachineDetectionSilenceTimeout`.

## 10. Media Streams (raw audio over WebSocket)

- **Unidirectional** (fork audio, call continues): `<Start><Stream url="wss://…" track="inbound_track|outbound_track|both_tracks" statusCallback="…"><Parameter name="k" value="v"/></Stream></Start>`. Stop with `<Stop><Stream name="…"/></Stop>` or REST `…/Calls/{CA}/Streams/{MZ}.json Status=stopped`.
- **Bidirectional** (you speak back; call blocks here): `<Connect><Stream url="wss://…"/></Connect>`. Inbound track only.
- Messages Twilio → you: `connected`, `start` (`streamSid`, `callSid`, `tracks`, `customParameters`, `mediaFormat: {encoding: "audio/x-mulaw", sampleRate: 8000, channels: 1}`), `media` (`track`, `chunk`, `timestamp`, `payload` base64), `dtmf` (bidirectional), `mark`, `stop`. All carry `sequenceNumber`, `streamSid`.
- You → Twilio (bidirectional): `{"event":"media","streamSid":"MZ…","media":{"payload":"<base64 mulaw 8k, no headers>"}}`, `{"event":"mark","streamSid":…,"mark":{"name":"x"}}` (echoed back when playback reaches it), `{"event":"clear","streamSid":…}` (flush buffered audio — for barge-in).
- `wss://` only; signature is sent on the WebSocket upgrade request (`X-Twilio-Signature`) — validate it.

## 11. ConversationRelay (voice AI agents)

`<Connect action="/relay-done"><ConversationRelay url="wss://…" welcomeGreeting="Hi! How can I help?" language="en-US" ttsProvider="ElevenLabs|Google|Amazon" voice="…" transcriptionProvider="Deepgram|Google" interruptible="any|speech|dtmf|none" dtmfDetection="true" hints="…"/></Connect>`

Twilio handles STT + TTS + barge-in; your WebSocket exchanges **text JSON**:
- Twilio → you: `setup` (callSid, from, to, custom params), `prompt` (`voicePrompt` transcript, `lang`, `last`), `interrupt` (what was spoken before barge-in), `dtmf`, `error`.
- You → Twilio: `{"type":"text","token":"Sure, ","last":false}` (stream LLM tokens; end with `last:true`), `play` (audio URL), `sendDigits`, `language` (switch STT/TTS), `end` (with `handoffData` JSON → delivered to `action` URL as `HandoffData`, e.g., to transfer to an agent).
- Action callback: `SessionStatus`, `SessionDuration`, `HandoffData`, error info.
Use ConversationRelay unless you need raw audio (then Media Streams + your own STT/TTS).

## 12. Client SDKs, TwiML Apps, SIP

- **TwiML App** (`AP…`, `/Applications.json`): a named set of Voice/SMS URLs; numbers or Access Tokens reference it. Voice SDK outgoing calls hit the TwiML App's `VoiceUrl` with your custom params + `To`.
- Voice JS/iOS/Android SDK: server mints an Access Token with `VoiceGrant(outgoing_application_sid=AP…, incoming_allow=True)` and identity; browser calls `device.connect({params:{To:"+1…"}})`; inbound to a client uses `<Dial><Client>alice</Client></Dial>`. Mobile push needs Push Credentials (`CR…`).
- **SIP Domains** (register SIP phones to Twilio → TwiML), **Elastic SIP Trunking** (`trunking.twilio.com/v1`, PSTN connectivity for PBXs, no TwiML), **BYOC** (your carrier into Twilio Voice).
- **Voice Dialing Geo Permissions** block risky destinations (21215 if blocked). Keep them tight to prevent toll fraud.
- Voice Insights (`insights.twilio.com/v1/Voice/{CA}/Summary`) for call quality & post-call analytics.

## 13. Gotchas

- 11200/11205 on answer = TwiML server unreachable/slow → caller hears "an application error has occurred". Set `VoiceFallbackUrl`.
- 12100 = invalid XML (unescaped `&`, HTML error page).
- `Twiml` param limit is 4000 chars — use `Url` for bigger docs.
- Trial accounts: calls only to verified numbers, with a trial preamble.
- `From` must be a Twilio number or verified outgoing caller ID (21210/21212).
- `<Dial>` without `answerOnBridge="true"` answers the inbound leg immediately (billing starts, caller hears silence/ringtone you choose).
- Status `completed` doesn't mean a human answered — check `AnsweredBy` or `DialCallStatus`.
- Recording URLs without `.mp3`/`.wav` return metadata/XML, not audio.
