# Sollu: Voice-Note Errand Agent

Sollu is a voice-note errand agent built for the All Things Agentic Hackathon (Taskmaster track). 

A spoken voice note is sent to Gemini, decomposed into discrete tasks, and each task is triaged into a lane (`now`, `next`, `later`). The distinguishing feature is the **trust ladder**: the agent starts by asking permission for every task class (e.g. `message_person`, `make_call`, `watch_price`), and promotes a class to auto-execute once enough approvals have accrued. Rejections demote it back.

## Safety and Guardrails

Sollu's safety story is inherently built into its core mechanic—the **Trust Ladder**. Rather than bolting on an opaque guardrails layer, Sollu provides verifiable, progressive autonomy:

- **No Implicit Execution**: Nothing irreversible executes without explicit user approval. All new task classes start at a baseline of `pending_approval`.
- **Earned Autonomy**: Autonomy is earned strictly per-class (e.g., authorizing calendar access does not authorize making phone calls). 
- **Instant Revocation**: A single rejection of an auto-executed task serves as a strong demotion signal, instantly resetting the agent's autonomy for that class back to zero.
- **Secure Asynchronous State Mutation**: Deferred lane evaluation relies on a protected HTTP push endpoint. The `POST /api/cron/deferred` route is strictly secured behind an `X-Cron-Secret` header to prevent unauthenticated mutation of task states. External condition evaluators (such as flight prices or weather APIs) are structurally stubbed to guarantee deterministic execution for the demo without compromising the evaluation mechanic.
- **Full Observability**: Every autonomy change—promotions, demotions, and ladder consultations, and deferred task checks—is logged with strict correlation IDs, providing a fully auditable lifecycle of every voice note.

*Note on Architecture: The trust ladder directly influences the triage pipeline. The triage logic natively consults the ledger before a task is even scheduled, directly mapping user-granted authority to system execution boundaries.*
