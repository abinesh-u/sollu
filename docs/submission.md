# Sollu

**Deployed:** https://voice-agent-155260241110.asia-south1.run.app
**Hackathon:** All Things Agentic Hackathon — Taskmaster track

## Elevator Pitch

Say it once — Sollu turns a voice note into triaged, executed tasks, and earns autonomy where autonomy is safe.

## The Problem & Inspiration

A voice note after a meeting hides five errands — email mom, add milk, look up flights, note the rent, watch a price. It never gets done, because turning a ramble into five finished things takes more effort than you have left when you record it.

Assistants make this worse two ways: asking permission for everything is a chore; auto-running everything — including your emails — is reckless before it's earned any trust. People don't extend trust uniformly either. You'd let someone touch your to-do list long before your inbox. Sollu works the same way, and tracks that trust separately for every kind of task.

## What it Does

- A voice note goes to Gemini, which splits it into tasks and sorts each into a lane: `now` / `next` / `later`.
- Each task also gets a class — email, to-do, Notion page, research, price-watch — and a risk tier:
  - **Read-only** — runs instantly.
  - **Soft** (to-do, Notion) — asks, then auto-runs once *that class* earns enough approvals.
  - **Hard** (email) — always asks, no exceptions, ever.
- Approval isn't a checkbox — it runs a real action (Gmail sends, Tasks adds, Notion creates, research searches) and the result lands on the card. A second model reads a spoken confirmation.

## How We Built It

- **Pipeline** — FastAPI on Cloud Run hands off to a real Google ADK agent (`VoiceAgent` on an ADK Runner) sitting directly on the live request path, which calls the orchestrator, which asks `gemini-3.5-flash` to decompose the note in one structured, schema-typed call.
- **Trust ladder** — per-class thresholds in Firestore: 0 approvals (read-only), 3 (soft), never (hard). Crossing one logs a promotion event.
- **Execution** — an MCP client calls real tools (Gmail, Tasks, Notion), each call carrying an idempotency key so a retry can't double-send. Manual approvals run inline; auto-approvals run in the background.
- **Stack** — `gemini-3.5-flash` (all reasoning) + `gemini-2.5-flash-tts` (confirmation only) + Firestore + Cloud Run + a React/Vite frontend with a live trust-ladder view.

## Challenges We Overcame

- **Grounded search + schema, 244s → 18.7s.** Web-grounded research was unusable without a response schema. Pairing `google_search` with `response_schema` made it fast *and* structured.
- **Grounding metadata lies if misread.** The model's own `sources` field points at dead redirect links. We had to read `grounding_metadata.domain` directly — and caught a case where a finding from IDC was mislabeled under a bare "GOOGLE.COM" source chip.
- **Real actions, real risk.** Once approval calls real Gmail/Notion/Tasks tools, a retry can double-send. Fixed with a hash-based idempotency key built from the note, task, and arguments.
- **The trust ladder needed a rebuild.** It started as one global approval counter, which broke immediately in practice — rebuilt so each task class tracks its own approvals independently in Firestore.

## Accomplishments That We're Proud Of

- **The Google Agent Framework requirement is load-bearing, not decorative.** The ADK agent sits on the live `POST /tasks` path — every real request runs through it, not a demo-only wrapper.
- **A trust model with real teeth.** Hard tasks like sending email structurally can never auto-run, no matter how many approvals pile up. We diverged from the hackathon's literal "ask 3x, then auto-run everything" guideline because a ladder that eventually emails on its own is the wrong product.
- **Actually deployed.** ~6.5s median end-to-end on Cloud Run, upload to task cards — measured on the live system, not a laptop.

## What We Learned

- Trust isn't one number — it has to be keyed per task class, or it's meaningless.
- Real actions need idempotency; a read-only agent never teaches you that.
- Model region and infra region are independent decisions — an expensive lesson to learn once.
- Don't trust a model's confidence at face value; read the structured metadata instead.
- Some bugs only exist on the rendered page, never in the diff.
- Labeling a stub honestly in the UI makes the real parts more believable, not less.

## What's Next for Sollu

- Grow into the classes already scoped in our own roadmap doc — instant-trust read-only Workspace access (read email, check calendar, search Drive), more auto-promotable medium-risk actions (draft email, calendar events, expense logging), and explicitly-never-auto high-risk ones (sharing or deleting a Drive file, deleting a Notion page). Also: a real price source — `watch_price` still returns a canned value.
- Use `grounding_supports` to verify individual claims, not just flag `grounded: true` for a whole answer.
- Real undo for soft tasks — right now a rejection only affects future trust, not an action that already ran.
- Let Sollu act proactively — ambient triggers, pattern detection — instead of only reacting to a voice note.
- **A real memory layer.** Today every note starts cold — the agent runner keeps state in memory for one session and forgets it after. Persistent memory is what lets trust go from per-class to per-person: mom vs. a stranger, same task class, different trust.
- Long-term, the trust ladder itself — reversibility-gated autonomy — is the reusable part. Less a hackathon feature, more infrastructure other agents could sit behind.
