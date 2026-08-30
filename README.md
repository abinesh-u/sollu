# Sollu: Voice-Note Errand Agent

Say it once — Sollu turns a voice note into triaged, executed tasks, decided by a
**trust ladder**: read-only tasks auto-run instantly, soft tasks (to-do, Notion) earn
auto-run per class after 3 approvals, hard tasks (email) never auto-run. Approval isn't a
checkbox — it runs a real executor and puts a real artifact on the card.

**Deployed:** <https://voice-agent-155260241110.asia-south1.run.app>

## Built With

| Layer | Choice |
|---|---|
| Reasoning (triage, extraction, every executor) | `gemini-3.5-flash` |
| Agent framework | `google-adk` — `src/agent.py`'s `VoiceAgent` sits on the live `POST /tasks` path |
| Compute + state | Cloud Run + Firestore Native, `asia-south1` |
| External actions | MCP client → Gmail, Google Tasks, Notion |

---

## Repository Structure

```
.
├── main.py
├── src/
│   ├── agent.py
│   ├── mcp_server.py
│   ├── domain/
│   │   ├── orchestrator.py
│   │   ├── parser.py
│   │   ├── trust_ladder.py
│   │   ├── executor_runner.py
│   │   ├── evaluator.py
│   │   ├── intents.py
│   │   ├── task_repo.py
│   │   ├── speaker.py
│   │   ├── vertex.py
│   │   └── logger.py
│   └── executors/
│       ├── mcp_executor.py
│       ├── gemini_executors.py
│       ├── price_executor.py
│       ├── base.py
│       └── registry.py
├── frontend/src/components/
├── tests/
├── scripts/
│   ├── ops/
│   ├── dev/
│   ├── eval/
│   └── fixtures/sample.wav
└── docs/submission.md
```

---

## Implementation Insights

- **Reversibility, not frequency, sets the threshold.** `TrustLadderEngine._get_threshold`: `0` read-only, `3` soft, `None` (never) hard — tracked per class in Firestore, so `add_todo_task` and `create_notion_page` earn trust independently. Hard tasks structurally can't promote, no matter how much trust accrues elsewhere.
- **Idempotency on real actions.** `McpExecutor` hashes `note + intent + args` per MCP call, so a retry can't double-send a real email.
- **Grounded search + schema compose.** 244s without `response_schema`, 18.7s with it. `executor_runner._run_with_deadline` enforces a real wall-clock deadline itself — `HttpOptions.timeout` is an httpx read timeout, not one.
- **Grounding read from metadata, not prose.** The model's own `sources` field is a dead redirect link; real source is `grounding_metadata.grounding_chunks[].domain` (sometimes `None` — caught an IDC finding mislabeled "GOOGLE.COM").
- **Model region ≠ infra region.** `gemini-3.5-flash` isn't PAYG in `asia-south1`; called at the `global` endpoint while Cloud Run/Firestore stay regional.
- **Safety is the ladder, not a bolt-on.** Every class starts `pending_approval`; one rejection resets it to zero; `POST /api/cron/deferred` requires `X-Cron-Secret`; every step logs by `correlation_id`.
- **TTS is kept dumb.** Gets one finished sentence, never audio/transcript/task text; failure degrades silently to text.

---

## Where to Look

| Claim | Verify it here |
|---|---|
| ADK agent is on the live path | `main.py:92` → `src/agent.py:64` (`run_voice_agent`) → `:47` (`VoiceAgent`) |
| Reversibility-gated thresholds | `src/domain/trust_ladder.py:10-19` |
| Trust tracked per class | one Firestore doc per class; classes in `src/domain/intents.py` |
| MCP execution is real | `src/executors/mcp_executor.py` |
| No double-send on retry | `mcp_executor.py:24-33` (`_get_idempotency_key`), used at `:87` |
| Grounding from metadata | `gemini_executors.py:97-105` |
| Search + schema compose | `gemini_executors.py:59,84-86` |
| Real wall-clock deadline | `executor_runner.py:34-41` |
| Cron route is authenticated | `main.py:38,190` |
| Run the stability check first | `uv run python scripts/ops/positive_control.py --runs 5` |

## What Approval Actually Does

| Class | Executor | Real or stub |
|---|---|---|
| `send_email` | MCP (Gmail) | **real** |
| `add_todo_task` | MCP (Google Tasks) | **real** |
| `create_notion_page` | MCP (Notion) | **real** |
| `research` | Gemini + Google Search | **real, web-grounded** |
| `watch_price` | Deferred evaluator | **stubbed price source** |
| `other` | none | `no_executor` |

`GET /api/classes` exposes live executor status. Manual approval runs inline; auto-approval runs in the background.

---

## Setup (local)

**No setup:** use <https://voice-agent-155260241110.asia-south1.run.app>.

**Spine only:**
```bash
gcloud auth application-default login
# set GOOGLE_CLOUD_PROJECT in .env
uv run uvicorn main:app --reload --port 8080
```
Workspace actions degrade to a "Draft/Queued" simulation, not failure — the ladder's floor, not a gap. Upload `scripts/fixtures/sample.wav` to test without speaking.

**Full Workspace (real Gmail/Tasks):**
1. Web-app OAuth client in GCP, redirect URI `http://localhost:8080/oauth/callback`
2. Fill `.env` from `.env.example` (`GOOGLE_CLIENT_ID/SECRET`, `SETUP_PASSWORD`)
3. Visit `/oauth/start?password=<pw>`, authorize — token saved to Firestore

*Testing-status consent screens expire refresh tokens after 7 days; re-run `/oauth/start` if auth fails.*

```bash
cd frontend && npm install && npm run build && cd ..
uv run uvicorn main:app --reload --port 8080
# hot reload: cd frontend && npm run dev
```

## Deploy (Cloud Run)

```bash
uv export -o requirements.txt --no-hashes && sed -i '' '/^-e \.$/d' requirements.txt

gcloud run deploy voice-agent --source . --project <your-gcp-project> \
  --region asia-south1 --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=<your-gcp-project>,GOOGLE_CLOUD_LOCATION=asia-south1,GOOGLE_GENAI_USE_VERTEXAI=TRUE,CRON_SECRET=<your-secret>
```

No Dockerfile — buildpack from `--source .`. No IPv6 route to Google locally? Deploy from [Cloud Shell](https://cloud.google.com/shell) or `networksetup -setv6off Wi-Fi`.

## Testing

```bash
uv run python -m unittest discover -s tests             # unit tests
uv run python scripts/ops/positive_control.py --runs 5  # stability check: count+lane+class
uv run python scripts/eval/test_agent.py                # smoke test, full ADK path
```
