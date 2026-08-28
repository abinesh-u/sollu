# Sollu: Voice-Note Errand Agent

Sollu is a voice-note errand agent built for the All Things Agentic Hackathon (Taskmaster track). 

A spoken voice note is sent to Gemini, decomposed into discrete tasks, and each task is triaged into a lane (`now`, `next`, `later`). The distinguishing feature is the **trust ladder**: the agent starts by asking permission for every task class (e.g. `message_person`, `make_call`, `watch_price`), and promotes a class to auto-execute once enough approvals have accrued. Rejections demote it back.

## Models

| Purpose | Model |
|---|---|
| Triage, extraction, and every executor | `gemini-3.5-flash` |
| Spoken confirmation only | `gemini-2.5-flash-tts` |

All reasoning runs on **`gemini-3.5-flash`**. The secondary model is output-only: it is
handed one finished sentence, built in Python from counts the pipeline has already
computed, and reads it aloud. It never touches triage, extraction, execution, or the
trust ladder, it never receives the audio or a transcript, and if it fails the app is
unchanged — spoken confirmation is off by default and degrades silently to the text
summary.

## What approval actually does

Approving a task runs an executor for its class, and the artifact appears on the card.

| Class | Executor | Real or stub |
|---|---|---|
| `research` | `gemini-3.5-flash` with Google Search grounding | real, web-grounded |
| `message_person` | `gemini-3.5-flash` draft message | **draft only — never sent** |
| `make_call` | `gemini-3.5-flash` call script | **script only — no call placed** |
| `watch_price` | Deferred condition evaluator | **stubbed price source** |
| `other` | none | reports `no_executor` |

Grounding is reported from the response's `grounding_metadata`, never inferred from the
prose, so a "Web-grounded" tag means a search actually ran. `GET /api/classes` exposes
each class's executor status.

Manual approval executes inline. Auto-approval executes in a background task so upload
latency stays flat — a grounded research call takes ~10–17s and runs per task — and the
card shows an `executing` state until the artifact lands.

## Input

A voice note can be recorded in the browser or uploaded as a file. An optional image
travels in the **same** `gemini-3.5-flash` request as a second content part, and is
treated as supporting evidence for what the speaker said rather than a second source of
tasks; what it contributed is recorded in `source` and `evidence`.

## Safety and Guardrails

Sollu's safety story is inherently built into its core mechanic—the **Trust Ladder**. Rather than bolting on an opaque guardrails layer, Sollu provides verifiable, progressive autonomy:

- **No Implicit Execution**: Nothing irreversible executes without explicit user approval. All new task classes start at a baseline of `pending_approval`.
- **Earned Autonomy**: Autonomy is earned strictly per-class (e.g., authorizing calendar access does not authorize making phone calls). 
- **Instant Revocation**: A single rejection of an auto-executed task serves as a strong demotion signal, instantly resetting the agent's autonomy for that class back to zero.
- **Secure Asynchronous State Mutation**: Deferred lane evaluation relies on a protected HTTP push endpoint. The `POST /api/cron/deferred` route is strictly secured behind an `X-Cron-Secret` header to prevent unauthenticated mutation of task states. External condition evaluators (such as flight prices or weather APIs) are structurally stubbed to guarantee deterministic execution for the demo without compromising the evaluation mechanic.
- **Full Observability**: Every autonomy change—promotions, demotions, and ladder consultations, and deferred task checks—is logged with strict correlation IDs, providing a fully auditable lifecycle of every voice note.

*Note on Architecture: The trust ladder directly influences the triage pipeline. The triage logic natively consults the ledger before a task is even scheduled, directly mapping user-granted authority to system execution boundaries.*
