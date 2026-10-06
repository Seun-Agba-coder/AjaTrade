# Spec: Voice-Note Onboarding for AjaTrade

## 1. Goal

AjaTrade already has a complete onboarding pipeline for users who message the bot by **text**. This feature adds a parallel pipeline for users who **cannot read or write** and can only send **voice notes (VNs)**.

A first-time user whose first message is a VN must be taken through: language detection, consent, user type, then the main menu. Every instruction is delivered as a VN in the user's own language, with an interactive WhatsApp message beneath it.

Design assumption: the user cannot read the buttons. Every interactive message is paired with a VN that explains what each option means, and every interactive step must also be answerable by voice (see 6.3).

## 2. Instructions for the implementing agent

The voice pipeline is a **separate implementation** from the text pipeline. The text onboarding is the reference, and the voice onboarding is built as its own copy, adapted to voice.

Do this before writing any code:

1. Read the existing text onboarding pipeline closely: its state machine, consent handling, user-type handling, main menu sender, message formatting and error handling. Treat it as the template.
2. Build the voice pipeline as its own module (for example a `voice/` folder) by copying the text implementation's structure, naming conventions, state transitions and storage calls, then changing each step to use the voice mechanics in this spec (transcription, language detection, cached VNs, interactive messages paired with a VN, voice replies to buttons).
3. **Do not modify the text pipeline's files**, except for the minimal change in the webhook handler that sends audio messages to the voice pipeline. The text flow must behave exactly as before.
4. Do not import handlers from the text pipeline into the voice pipeline. Low-level utilities that are not onboarding logic (WhatsApp send and download helpers, the Groq client, the translation and Spitch TTS pipeline, the database client) may be imported and shared, because duplicating those would only create two things to keep in sync.
5. Use the same user record schema and the same state names and values as the text flow. Do not create a second collection or a different set of states. A user may start with a VN and later send text, or the reverse, and both pipelines must read the same record and agree on where the user is.
6. Report the findings in a short note before implementing, listing the text flow's states, storage fields and menu sender, so gaps between this spec and the codebase are visible.

Where this spec conflicts with how the existing code works, prefer the existing code's conventions and flag the conflict.

## 3. Supported languages

| Code | Language |
|------|----------|
| yo | Yoruba |
| ha | Hausa |
| ig | Igbo |
| pcm | Nigerian Pidgin |
| en | English |

Anything else is "unsupported".

## 4. User-facing flow

### Trigger

A message arrives from a phone number with no existing user record (or with an onboarding state of `NEW`), and the message type is audio.

The content of the VN does not matter. Whatever was said, the first VN always starts onboarding.

### Step 1: Language detection

1. Download the VN from WhatsApp (media URLs are short-lived and need the access token).
2. Transcribe it with the Groq speech-to-text model already configured in the project.
3. Send the transcript to an LLM classifier. It returns strict JSON:
   ```json
   { "language": "yo|ha|ig|pcm|en|other", "confidence": 0.0, "detected_other": "free text or null" }
   ```
4. Apply these rules in order:
   - Audio under about 1 second, silent, or empty transcript: treat as low confidence.
   - Mixed speech (very common, e.g. Yoruba and English): if a supported local language (yo, ha, ig) is clearly present, choose it. English-only speech is `en`. Pidgin is `pcm`.
   - `confidence` below the threshold (config value, start at 0.6): go to the low-confidence path.
   - `language` is `other`: go to the unsupported path.
   - Otherwise: save the language and continue.

Save on the user record: detected language, confidence, language source, and the timestamp of the first VN. Hold the transcript and the original audio reference only provisionally; they are kept if the user accepts consent and discarded if the user declines (see 6.6).

### Low-confidence path

- First failure: send a VN in English and Pidgin asking them to send another VN, speaking slowly in a quiet place. State stays `AWAITING_LANGUAGE`.
- Second failure: default the user to Pidgin. Set `language = pcm`, `language_source = "default_fallback"`, and keep the real (low) confidence. Send a short VN in Pidgin (script `pidgin_default_notice`) and continue straight to Step 2 in Pidgin. Do not show a language list: the users this flow is for cannot rely on reading it.
- If a later VN from a user with `language_source = "default_fallback"` is detected as a supported language with confidence above the threshold, update their language to it and set `language_source = "detected"`. Later messages then use the new language.

### Unsupported path

Send one VN in English (as decided). Source script `unsupported_language` is in section 7.

Then:
- State becomes `UNSUPPORTED_LANGUAGE`. Store the phone number, detected language label (`detected_other`), transcript and timestamp. This is useful data on which languages users ask for next.
- Do not send anything else automatically. No follow-ups, no reminders.
- If the same number sends another VN, run detection again from Step 1. A user who retries in a supported language proceeds normally.
- Cap the unsupported reply at one per 24 hours per number to avoid a loop if the user keeps sending VNs in the same language. Further VNs in that window are stored but get no reply.

### Step 2: Welcome and consent

Send, in this order, awaiting each send before the next so ordering is preserved:

1. A VN in the user's language: what AjaTrade is, that we would like to save their chat and phone number, and what each button means (script `welcome_consent`).
2. An interactive reply-button message in the user's language with two buttons:
   - `1 Accept`
   - `2 Decline`

State becomes `AWAITING_CONSENT`.

On the response, store `consent_status` (`accepted` or `declined`) and `consent_timestamp`. Both answers move to the next step.

### Step 3: User type

Send, in order:

1. A VN in the user's language. It starts with a short acknowledgement that depends on the consent answer (`consent_accepted_ack` or `consent_declined_ack`), then explains the options (script `user_type_prompt`): press 1 if you are a farmer, 2 if you are a trader, 3 if you are something else.
2. An interactive reply-button message with three buttons:
   - `1 Farmer`
   - `2 Trader`
   - `3 Other`

State becomes `AWAITING_USER_TYPE`. On the response, store `user_type` (`farmer`, `trader`, `other`).

### Step 4: Main menu

Send, in order:

1. A VN in the user's language introducing the menu and explaining what each number does (script `menu_intro`), starting with "press 1 to get help diagnosing a crop problem". The remaining items are generated from the menu already defined in the code, in the same order, as "press N for ...".
2. The existing main menu interactive message, in the user's language.

State becomes `ONBOARDED`.

### Returning users who send VNs

The main menu is currently only sent when an incoming message is text, because no voice pipeline exists yet. This is not a bug to fix; it is part of what the voice pipeline must build.

In the webhook handler, add a branch so that incoming audio messages go to the voice pipeline. For an `ONBOARDED` user who sends a VN, the voice pipeline must produce the same behavior the text pipeline produces for an onboarded user: look at how the text path decides when to send the menu and how it routes a message to a feature, and copy that logic into the voice module, using the transcript as the message text. If the text path shows the menu only on certain triggers (first message of a session, a keyword), apply the same rule to VNs.

## 5. State machine

```
NEW
 └─ first VN received ─► AWAITING_LANGUAGE
      ├─ unsupported ──────────► UNSUPPORTED_LANGUAGE ─(new VN)─► AWAITING_LANGUAGE
      ├─ low confidence x2 ────► default to Pidgin ─► AWAITING_CONSENT
      └─ language saved ───────► AWAITING_CONSENT
                                    └─ accept/decline ─► AWAITING_USER_TYPE
                                                            └─ 1/2/3 ─► ONBOARDED
```

Map these names to the states the text flow already uses and store the text flow's exact values, so both pipelines read the same record. Only add a new state where the voice flow has a step the text flow does not have (for example `UNSUPPORTED_LANGUAGE`), and make sure the text pipeline treats an unknown state safely.

An interactive message is only handled when the user's state expects it. A stale button tap from an earlier step must be ignored, or answered with a gentle replay of the current step, and must not change state.

## 6. Cross-cutting requirements

### 6.1 Audio format

VNs sent to the user must be OGG/Opus so WhatsApp displays them as voice notes (play button with waveform) rather than as audio file attachments. Confirm the TTS output format and convert with ffmpeg if needed. Set the voice flag if the send API requires it.

### 6.2 Interactive message limits

- Reply buttons: maximum 3 buttons, title maximum 20 characters.
- List messages: maximum 10 rows, row title maximum 24 characters.
- Body text is limited to 1024 characters.

Translated labels must be checked against these limits when the assets are generated. If a translation is too long, fail the generation with a clear error and use a shorter translation. Never truncate silently.

Keep the number at the front of each label (`1 Accept`). The VN refers to options by number and position, so users can match what they hear to what they see even if they cannot read the words.

### 6.3 Voice replies to interactive steps

A user who cannot read may reply to a button prompt with a VN instead of tapping. When the state is `AWAITING_CONSENT` or `AWAITING_USER_TYPE`, and an audio message arrives:

1. Transcribe it.
2. Use the LLM to map it to one of the valid options for that step (for example "yes / I agree / ok" maps to accept; "one", "I am a farmer" maps to option 1). Include the user's language in the prompt.
3. If it maps with sufficient confidence, treat it exactly as if the button was tapped.
4. If not, replay the VN for the current step once, then stay in the same state. Do not loop more than twice; after that, send nothing and wait.

### 6.4 Pre-generated, cached audio

The onboarding scripts are fixed text. Do not generate audio per user.

- Generate each script once per language through the existing translation and TTS pipeline, store the audio file in the existing storage bucket, and key it by `script_id + language + hash(source_text)`.
- Changing the source text changes the hash and triggers regeneration.
- WhatsApp media IDs expire (about 30 days). Cache the file, and if a send fails because a media ID is invalid, re-upload from the stored file and retry.
- Provide a small script or admin command that (re)generates all onboarding assets, and a startup check that logs which assets are missing.

### 6.5 Reliability

- Deduplicate incoming webhook events by WhatsApp message ID. WhatsApp retries deliveries, and a duplicate must not send a second welcome flow.
- Reject or ignore audio messages from numbers already in a terminal state only if the existing code does; otherwise route them as in section 4.
- If transcription or classification fails (API error), do not leave the user in silence. Send the low-confidence VN and log the error. Do not advance state.
- Log each transition with phone number (hashed in logs if the project already does this), old state, new state and message ID.

### 6.6 Data and consent

Store, on the existing user record: phone number, language (and its source and confidence), consent status and timestamp, user type, onboarding state, timestamps.

Decision from the product owner: for users who decline, store only their consent decision, language, user type and onboarding state (plus the phone number only as far as is needed to reply to them). Do not persist their chat content, transcripts of later messages, or audio, and do not use their messages for analytics. The same applies to the stored transcript of the first VN: keep it for `accepted` users only, and for `declined` users keep only the detected language and confidence. Because consent is asked after the first VN has been processed, discard the first VN's audio and transcript if the user declines.

## 7. Source scripts (English)

These are the source texts. Run each through the existing translation pipeline, then TTS. Have a native speaker review each language before launch, especially Yoruba, Hausa, Igbo and Pidgin.

Keep sentences short and simple. These are heard once, by people who may be on poor connections.

**`unsupported_language`** (sent in English only)
> Hello, thank you for your message. AjaTrade works in Yoruba, Hausa, Igbo, Nigerian Pidgin and English. We could not understand the language you used. Please send us another voice note in one of these languages, and we will be happy to help.

**`low_confidence_retry`** (English and Pidgin)
> Sorry, we could not hear you well. Please send another voice note. Speak slowly and stay in a quiet place.

**`pidgin_default_notice`** (sent in Pidgin)
> Sorry, we could not understand your language well. We will talk to you in Pidgin. Let us continue.

**`welcome_consent`**
> Welcome to AjaTrade. AjaTrade is a helper on WhatsApp for farmers and traders. You can send us a voice note about your farm or your business, and we will answer you in your language. To serve you well, we would like to save your phone number and our chat. Below this message there are two buttons. Press number 1, Accept, if you agree. Press number 2, Decline, if you do not agree. You can also just say "accept" or "decline" in a voice note.

Buttons: `1 Accept`, `2 Decline`

**`consent_accepted_ack`** (prefix for the next VN)
> Thank you. We will save your chat and your phone number.

**`consent_declined_ack`** (prefix for the next VN)
> No problem. You can still use AjaTrade.

**`user_type_prompt`**
> Now, tell us what describes you. Below this message there are three buttons. Press number 1 if you are a farmer. Press number 2 if you are a trader. Press number 3 if you are something else. You can also say "farmer", "trader" or "other" in a voice note.

Buttons: `1 Farmer`, `2 Trader`, `3 Other`

**`menu_intro`**
> You are all set. Below this message is our menu. Press number 1 if you want help to find out what is wrong with your crop. [Then, for each remaining item in the existing menu: "Press number N for ...", generated from the menu config in the same order.]

**`step_replay_unclear`**
> Sorry, we did not understand. Please press one of the buttons below, or say your choice in a voice note.

## 8. Acceptance criteria

1. New number sends a VN in Yoruba, Hausa, Igbo, Pidgin or English: language is detected and saved; the welcome VN plays in that language, followed by the Accept/Decline buttons.
2. New number sends a VN in an unsupported language (for example Tiv or French): receives the English VN once, no other messages, state `UNSUPPORTED_LANGUAGE`, data stored.
3. Same number then sends a VN in Hausa: onboarding continues normally.
4. Silent or very short VN: low-confidence VN is sent; on the second failure the user is defaulted to Pidgin (`language_source = "default_fallback"`), receives the Pidgin notice VN, and continues to consent in Pidgin.
4a. A user who declines has only consent decision, language, user type and state stored (no transcript, audio or later chat content).
5. Accept and Decline both advance to the user-type step, with the correct acknowledgement, and both store the decision and timestamp.
6. Tapping Farmer, Trader or Other stores `user_type` and sends the menu VN and menu.
7. Replying to any button step with a VN ("yes", "one", "I am a farmer") behaves the same as tapping.
8. An onboarded user sending a VN receives the same menu or routing as one who sent text.
9. Duplicate webhook delivery of the same message ID causes no duplicate messages.
10. The text onboarding flow behaves exactly as before (regression check), and no text pipeline files were changed apart from the webhook branch for audio.
11. All cached audio exists for all five languages, and button titles are within WhatsApp limits.

## 9. Implementation checklist

- [ ] Read and summarize the existing text onboarding: states, storage fields, consent and user-type handling, menu sender
- [ ] Create the separate voice module, copying the text flow's structure and conventions
- [ ] Add the audio branch to the webhook that hands VNs to the voice module (the only change outside it), with media download and dedupe by message ID
- [ ] Add transcription step using the configured Groq STT
- [ ] Add LLM language classifier with strict JSON output and confidence threshold in config
- [ ] Add language, confidence, source and transcript fields to the user record (only if missing)
- [ ] Implement the low-confidence path with the Pidgin default and later language correction
- [ ] Implement the unsupported path with the 24-hour reply cap and stored detection data
- [ ] Implement the voice onboarding steps using the text flow's state names and the same user record
- [ ] Create the script source file with all script IDs from section 7
- [ ] Generate translations and TTS audio for yo, ha, ig, pcm, en; convert to OGG/Opus; cache with hash keys
- [ ] Generate and validate translated button and list labels against WhatsApp length limits
- [ ] Implement send helpers: VN then interactive message, awaited in order
- [ ] Implement voice replies to interactive steps (6.3)
- [ ] Copy the text path's menu and routing rules into the voice module for onboarded users who send VNs
- [ ] Add transition logging and error fallbacks (6.5)
- [ ] Apply the consent data-handling rule in 6.6 (minimal storage and discarding the first VN's audio and transcript for declined users)
- [ ] Add tests or a manual test script covering the 11 acceptance criteria
- [ ] Native-speaker review of all translated scripts before launch
