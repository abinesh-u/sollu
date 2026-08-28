# Context for coding agents

Read this before writing any code in this repo.

## What this project is

A voice-note errand agent for the All Things Agentic Hackathon (Taskmaster track).
A spoken voice note is sent to Gemini, decomposed into discrete tasks, and each task
is triaged into a lane. The distinguishing feature is the **trust ladder**: the agent
starts by asking permission for every task class, and promotes a class to
auto-execute once enough approvals have accrued. Rejections demote it back.

Deadline: Monday 31 Aug 2026, 5:00pm PDT. Optimise for a working deployed system,
not for elegance.

## Locked decisions — do not re-litigate

| Decision | Value |
|---|---|
| GCP project | `sixth-radar-506906-i1` |
| Model (triage, extraction, executors) | `gemini-3.5-flash` |
| Secondary model (spoken confirmation ONLY) | `gemini-2.5-flash-tts` |
| Model endpoint region | `global` (NOT asia-south1) |
| Infra region (Cloud Run, Firestore) | `asia-south1` |
| Firestore mode | Native |
| Service account | `voice-agent@sixth-radar-506906-i1.iam.gserviceaccount.com` |
| Package manager | `uv` |
| Deploy | Cloud Run buildpack via `--source .`, no Dockerfile |
| Thinking budget | `0` for triage (verified: correct output, 3.2s p50 post-M10) |

Why global endpoint: Gemini 3.5 Flash is only offered as Single Zone Provisioned
Throughput in asia-south1, so it is not reachable pay-as-you-go from Mumbai.
Model region and infra region are independent.

## Model split — do not blur this

| Purpose | Model |
|---|---|
| Triage, extraction, all executors | `gemini-3.5-flash` |
| Spoken confirmation only | `gemini-2.5-flash-tts` |

`gemini-3.5-flash` does all of the reasoning, which is what the hackathon's
"Gemini 3.5 or newer" requirement is about. The TTS model is output-only: it is
handed one finished English sentence, built in Python from counts already
computed, and voices it. It never touches triage, extraction, executors, or
anything on the critical path, and it never sees the audio or the transcript.
If it fails the app behaves exactly as before — verified by pointing it at a
bogus model string.

`gemini-3.1-flash-live` does NOT exist; it 404s as a Vertex publisher model. The
audio-capable models on this project are `gemini-2.5-flash-tts`,
`gemini-2.5-pro-tts`, `gemini-live-2.5-flash-native-audio` and
`gemini-omni-1.1-flash-preview`.

Never say "built on Gemini 2.5", and never imply the secondary model reasons.

## Stale-knowledge warning

`gemini-3.5-flash` and `google-adk` 2.8.0 are newer than your training data.

- Do NOT substitute a model string you recognise. `gemini-2.0-flash` and
  `gemini-2.5-flash` are both WRONG — 2.5 fails the hackathon's mandatory
  "Gemini 3.5 or newer" requirement.
- Do NOT write ADK APIs from memory. Read the installed source in `.venv` or the
  official docs before using any ADK class or method.
- If unsure whether something exists, check it. Do not assert.

## Ground truth that must keep working

`scripts/round_trip_audio.py` is a verified working path from a `.wav` file to
structured JSON. It passed a 5/5 deterministic stability test. Do not refactor it
without re-running that test.

Verified output shape:

```json
{"tasks": [{"task": "Call the plumber", "lane": "now"}]}
```

Lanes are `now` | `next` | `later`.

**Pending schema change:** add a `class` field (e.g. `message_person`, `make_call`,
`watch_price`). The trust ladder accrues approvals per class, not per lane. The
ledger cannot work without this.

## Firestore layout

One document per task. Never a shared mutable blob — concurrent agents must not
contend for a single store. Approval history lives in its own collection keyed by
task class.

Log the token breakdown (audio / text / candidate / total) on every task document.
Cost per note is a scored operational metric.

## Working rules

- Small, runnable commits. Judges execute this repo and check it does what the
  submission claims — code that looks right but doesn't run is worse than less code.
- After any change touching the model call, re-run the round-trip script.
- Never commit `.env`. `.env.example` is the committed template.
- After changing `pyproject.toml`, regenerate requirements.txt:
  `uv export -o requirements.txt --no-hashes && sed -i '' '/^-e \.$/d' requirements.txt`
- Do not add dependencies without asking. Every new package is deploy risk.
- Do not claim a capability in code comments, README, or UI copy that isn't
  actually implemented.

## Out of scope

- Bidirectional live streaming API (wrong shape, and not needed: M12's spoken
  confirmation is one-way — a single generate_content call, no session, no websocket)
- Dockerfile
- Real Workspace OAuth if drafts-held-for-approval is sufficient
- Any further modality beyond M10's image input and M11's mic capture, both of
  which are deployed
