# Architecture

Sollu: a voice note goes in, Gemini decomposes it into tasks, and each task
walks a per-class **trust ladder** that decides whether it executes now or
waits for a human. Deployed on Cloud Run: <https://voice-agent-155260241110.asia-south1.run.app>

Rendered images for the submission form: [`architecture-system.png`](architecture-system.png)
and [`architecture-trust-ladder.png`](architecture-trust-ladder.png) (regenerate
with `npx -p @mermaid-js/mermaid-cli mmdc -i docs/architecture.md -o
docs/architecture.png -b white --scale 2` after editing a diagram below, then
rename the `-1`/`-2` output files it produces).

## System

```mermaid
flowchart TD
    Client["Browser — mic capture / file upload<br/>+ optional image"]

    subgraph CloudRun["Cloud Run · asia-south1 · sixth-radar-506906-i1"]
        direction TB
        Main["main.py — FastAPI adapter<br/>(shallow: routes only, no domain logic)"]

        subgraph AgentLayer["src/agent.py — Google Agent Framework mandatory"]
            Runner["InMemoryRunner + session"]
            VoiceAgent["VoiceAgent (ADK BaseAgent)"]
            Tool["FunctionTool: extract_tasks_from_audio"]
            Runner --> VoiceAgent --> Tool
        end

        subgraph Domain["Domain seam"]
            Orchestrator["TaskOrchestrator"]
            Parser["GeminiAudioParser"]
            Ladder["TrustLadderEngine"]
            Repo["TaskRepository"]
            Orchestrator --> Parser
            Orchestrator --> Ladder
            Orchestrator --> Repo
        end

        subgraph ExecPath["Auto-approved execution (background task)"]
            ExecRunner["executor_runner.run_auto_approved"]
            Registry["executors/registry"]
            GExec["gemini_executors<br/>research · message_person · make_call"]
            PExec["price_executor<br/>watch_price (stubbed)"]
            ExecRunner --> Registry --> GExec
            Registry --> PExec
        end

        Speaker["speaker.py — spoken confirmation<br/>(off by default, isolated)"]

        Main -- "POST /tasks" --> Runner
        Tool --> Orchestrator
        Main -- "queues auto_approved tasks" --> ExecRunner
        Main -- "POST /api/speak" --> Speaker
        Main -- "approve / reject / cron deferred" --> Orchestrator
    end

    ModelTriage["gemini-3.5-flash — global endpoint<br/>triage, extraction, every executor"]
    ModelTTS["gemini-2.5-flash-tts — global endpoint<br/>confirmation sentence → speech, output-only"]

    subgraph Firestore["Firestore · Native mode · asia-south1"]
        Tasks[("tasks<br/>one doc per task")]
        LadderColl[("trust_ladder<br/>keyed by task class")]
        Promo[("promotion_events")]
    end

    Client -->|"audio (+ image)"| Main
    Parser -->|"generate_content, response_schema"| ModelTriage
    GExec -->|"generate_content, google_search + response_schema"| ModelTriage
    Speaker -->|"generate_content"| ModelTTS
    Repo --> Tasks
    Ladder --> LadderColl
    Ladder --> Promo

    style AgentLayer fill:#eef,stroke:#557
    style ModelTriage fill:#fef3d5,stroke:#b8860b
    style ModelTTS fill:#fef3d5,stroke:#b8860b
    style Firestore fill:#e8f5e9,stroke:#2e7d32
```

Notes that matter for judging:

- **Google Agent Framework mandatory**: `main.py` calls `src/agent.run_voice_agent()`,
  not the orchestrator directly. The ADK `Runner` and `VoiceAgent` sit on the live
  request path — this is not a demo-only wrapper.
- **Model split**: all reasoning (triage, extraction, every executor) runs on
  `gemini-3.5-flash`. `gemini-2.5-flash-tts` only voices a sentence already built
  in Python from counts the pipeline computed — it never sees audio, transcript,
  or task text, and its failure degrades silently to the text summary.
- **Region split**: Cloud Run and Firestore run in `asia-south1`; both models are
  called against the `global` endpoint, because `gemini-3.5-flash` is only
  available in `asia-south1` as Single Zone Provisioned Throughput (not reachable
  pay-as-you-go). Infra region and model region are independent decisions.
- **Firestore layout**: one document per task (no shared mutable blob, so
  concurrent writers don't contend), approval counts in `trust_ladder` keyed by
  class, promotions appended to `promotion_events`.
- **Stubs, stated plainly**: `message_person`/`make_call` produce drafts —
  nothing is sent or called. `watch_price` reads a deterministic canned price.
  `research` is the one executor that is fully real and web-grounded.

## Trust ladder (the differentiator)

Each task **class** (`message_person`, `make_call`, `research`, `watch_price`, …)
carries its own independent approval count — approving a `research` task never
grants autonomy to `make_call`.

```mermaid
flowchart LR
    Start(("new class")) --> Pending["pending_approval<br/>approvals = 0..2<br/>each approve executes inline"]
    Pending -- "3rd approve<br/>write promotion_events" --> Auto["auto_approved<br/>new tasks of this class<br/>execute automatically, in background"]
    Auto -- "1 rejection<br/>approvals reset to 0" --> Pending

    style Pending fill:#eef,stroke:#557
    style Auto fill:#e8f5e9,stroke:#2e7d32
```

Rejecting a task that is still `pending_approval` leaves the class exactly
where it was — the ladder only moves on a promotion (3rd approval) or a
demotion (1 rejection while `auto_approved`).
