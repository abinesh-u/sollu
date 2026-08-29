# Context for coding agents

Read this before writing any code in this repo.

## What this project is

Sollu, a voice-note errand agent for the All Things Agentic Hackathon (Taskmaster
track). A spoken note is decomposed into tasks, each triaged into a lane
(`now` | `next` | `later`) and a class. The distinguishing feature is the **trust
ladder**: every task class starts by asking permission, and promotes to
auto-execute after 3 approvals. One rejection of an auto-approved task demotes it
to zero.

Approval is not bookkeeping — it runs an executor and puts a real artifact on the
card. That is the thing judges check, so keep it working.

Deployed: <https://voice-agent-155260241110.asia-south1.run.app>

Deadline: Monday 31 Aug 2026, 5:00pm PDT. Optimise for a working deployed system,
not for elegance.

## Locked decisions — do not re-litigate

| Decision | Value |
|---|---|
| GCP project | `sixth-radar-506906-i1` |
| Model endpoint region | `global` (NOT asia-south1) |
| Infra region (Cloud Run, Firestore) | `asia-south1` |
| Firestore mode | Native |
| Service account | `voice-agent@sixth-radar-506906-i1.iam.gserviceaccount.com` |
| Package manager | `uv` |
| Deploy | Cloud Run buildpack via `--source .`, no Dockerfile |
| Thinking budget | `0` for triage (verified: correct output; see Latency) |
| Auto-execute threshold | 3 approvals |

Why the global endpoint: Gemini 3.5 Flash is offered in asia-south1 only as Single
Zone Provisioned Throughput, so it is not reachable pay-as-you-go from Mumbai.
Model region and infra region are independent.

## Model split — do not blur this

| Purpose | Model |
|---|---|
| Triage, extraction, every executor | `gemini-3.5-flash` |
| Spoken confirmation only | `gemini-2.5-flash-tts` |

`gemini-3.5-flash` does all the reasoning, which is what the hackathon's "Gemini
3.5 or newer" requirement is about.

The TTS model is output-only. It receives one finished English sentence that
`src/domain/speaker.py` built in Python from counts already computed, and voices
it. It never sees the audio, the transcript, or task text, and it is never on the
path that decides anything. When it fails, `POST /api/speak` returns 204 and the
UI keeps its text summary.

Describe it that way in the README, the UI, and the video: primary
`gemini-3.5-flash`, secondary `gemini-2.5-flash-tts` for spoken confirmation.

## Verify before you assert

`gemini-3.5-flash` and `google-adk` 2.8.0 are newer than your training data, and
several things in this repo contradict what a model would guess. Check the
installed source in `.venv` or call the API; do not write an API from memory.

Model strings you may recognise are wrong here. `gemini-2.0-flash` and
`gemini-2.5-flash` both fail the "3.5 or newer" bar for the critical path.
`gemini-3.1-flash-live` does not exist at all — it 404s as a Vertex publisher
model. The audio-capable models on this project are `gemini-2.5-flash-tts`,
`gemini-2.5-pro-tts`, `gemini-live-2.5-flash-native-audio`, and
`gemini-omni-1.1-flash-preview`.

These cost hours to discover. Trust them over your priors:

- **`HttpOptions.timeout` is an httpx read timeout, not a wall-clock deadline.**
  A grounded call ran 244s under a 40s setting. `src/domain/executor_runner.py`
  enforces real deadlines itself with a thread pool. Keep it that way.
- **`google_search` and `response_schema` work together** on gemini-3.5-flash.
  The schema is also what keeps grounded latency sane: 18.7s with it, 244s
  without. Always pass it on the research call.
- **Read grounding from `grounding_metadata`** (`web_search_queries`,
  `grounding_chunks`) — never infer it from the prose. For source names use
  `GroundingChunkWeb.domain`; a model-supplied `sources` field returns
  unreadable `vertexaisearch…/grounding-api-redirect/…` URLs.
- **`gemini-2.5-flash-tts` returns raw PCM** (`audio/L16;codec=pcm;rate=24000`),
  which no browser plays from an `<audio>` element. `speaker.py` adds a 44-byte
  RIFF header server-side.
- **Audio containers:** `audio/webm`, `audio/ogg`, `audio/mp4` and `audio/wav`
  all parse, with or without a `;codecs=opus` suffix. `video/webm` returns 400,
  and MediaRecorder blobs are easy to label that way — `normalise_audio_mime`
  in `src/domain/orchestrator.py` rewrites a `video/*` prefix.
- **Disabling thinking with tools attached stalls the call** rather than
  erroring. `thinking_budget=0` is for triage only; executors leave it default.

## The gate

```
uv run python scripts/positive_control.py --runs 5
```

Runs `GeminiAudioParser.parse_audio` — the same code path `POST /tasks` uses —
against `/tmp/voice-test/positive.wav`, and exits non-zero if unstable. Run it
after any change touching the model call, the prompt, or the schema.

It gates on **count + lane + class**. Verbatim task text and array order vary run
to run even at `temperature=0`; nothing downstream consumes the wording, so an
exact-string gate would fail on an unchanged codebase and tell you nothing.

Current expected shape, 5/5 stable (re-verified 29 Aug against the deployed refactor):

```
now   / message_person    now  / make_call
next  / research          later / watch_price
```

Keep this script pointed at the production parser. An earlier version carried its
own client, prompt, and schema, drifted from the real prompt, and certified a
lane assignment that production did not produce.

## Latency — quote the deployed number

Measured 29 Aug 2026, after the repository refactor:

| Path | Median | Range |
|---|---|---|
| `parse_audio` locally (the gate) | 4.2s | 3.8s – 80s |
| `POST /tasks` end to end on Cloud Run | 6.5s | 5.2s – 6.8s |

The demo runs on Cloud Run, so **6.5s is the number to say out loud** — it covers
the upload, the model call, four Firestore writes and the ladder reads. An earlier
3.2s figure measured only the local parse and no longer reproduces.

The 80s local outlier is this machine, not the model: Cloud Run showed no outlier
across four consecutive uploads. See the IPv6 note under Deploying. Do not chase a
slow local call as a model regression before ruling that out.

## Look at the rendered page

Two defects reached the deployed site past clean structural checks: an artifact
indented by `white-space: pre-wrap` inheriting the template literal's own
indentation, and a recording indicator that never hid because a class setting
`display` outranks the UA's `[hidden] { display: none }`. Both were obvious on
sight and invisible to grep.

Screenshot the deployed page after a UI change:

```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
  --disable-gpu --virtual-time-budget=15000 --window-size=1500,1500 \
  --screenshot=/tmp/shot.png <url>
```

Headless cannot drive `MediaRecorder`, so mic capture needs a human click.

## Firestore layout

One document per task; never a shared mutable blob, so concurrent writers do not
contend. Approval counts live in `trust_ladder` keyed by task class; promotions
append to `promotion_events`.

Log the token breakdown (audio / text / candidate / total) on every task
document — cost per note is a scored metric.

Every log line carries the `correlation_id` of the note that produced it, so one
note's whole lifecycle greps out in order: note received → tasks extracted →
triage decision → ladder consulted → execution queued → execution complete.
Execution reads the id off the task document rather than minting a new one; keep
that.

## Working rules

- Small, runnable commits. Judges execute this repo and check it does what the
  submission claims — code that looks right but does not run is worse than less
  code.
- Say only what is implemented, in code comments, README, and UI copy alike. The
  drafts are drafts; the price source is a stub. Write it that way.
- `.env.example` is the committed template; `.env` stays out of git.
- After changing `pyproject.toml`, regenerate requirements.txt:
  `uv export -o requirements.txt --no-hashes && sed -i '' '/^-e \.$/d' requirements.txt`
- Ask before adding a dependency. Every new package is deploy risk.

## Deploying

`requirements.txt` is gitignored, and the buildpack needs it, so a clean clone
must regenerate it from the committed `uv.lock` before deploying.

Deploy from Cloud Shell when the local network misbehaves — this machine
advertises IPv6 with no route to Google, which makes Python and gcloud block for
minutes on the first connection while curl shrugs it off via happy-eyeballs.
`networksetup -setv6off Wi-Fi` fixes it locally; Cloud Shell sidesteps it.

`--min-instances=1` is set as of 29 Aug 2026 and must go back to 0 after the
demo window. It matters because: auto-approved tasks execute in a
background task after the response, and a scaled-down instance loses that work
silently.

## Still stubbed — say so, do not quietly fix

- Price and weather conditions (`src/domain/evaluator.py`) return deterministic
  canned answers so the deferred-lane mechanic demos reliably.
- `message_person` and `make_call` produce drafts. Nothing is sent, no call is
  placed, and the UI labels both.

## Out of scope

- Bidirectional live streaming. Spoken confirmation is one-way: one
  `generate_content` call, no session, no websocket.
- Dockerfile.
- Workspace OAuth, while drafts-held-for-approval demo identically.
- Executors that send, post, or call anything externally.
- Further modalities. Audio, image, and mic capture are deployed; that is enough.
