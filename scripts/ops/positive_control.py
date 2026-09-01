"""Positive-control audio round-trip against the PRODUCTION call path.

This runs `GeminiAudioParser.parse_audio` -- the same code `POST /tasks` uses.
It previously built its own client, prompt and schema, which had drifted from
the parser (no `class`/`condition` fields, and a prompt that lanes the Cloud SQL
task differently). A canary testing a prompt that isn't the one running
certifies nothing, so it now shares the parser outright.

The gate is count + lane + class, not verbatim task text. Phrasing and array
order vary run to run even at temperature 0 -- ordinary LLM non-determinism --
and nothing downstream consumes the wording: the trust ladder and the executors
consume `class` and `lane`. An exact-string gate would fail on an unchanged
codebase, which makes it useless as a regression signal.

Usage:
    uv run python scripts/positive_control.py --runs 5
"""

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.domain.parser import GeminiAudioParser


def signature(tasks: list) -> str:
    """The gated shape: how many tasks, and each one's lane and class.

    Sorted, so a reordered array is not treated as a regression.
    """
    return json.dumps(sorted([t.get("lane"), t.get("class")] for t in tasks))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default="scripts/fixtures/sample.wav")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--log", default="logs/runs.jsonl")
    ap.add_argument(
        "--budget",
        type=int,
        default=None,
        help="accepted for backwards compatibility and ignored -- "
        "thinking_budget is owned by GeminiAudioParser",
    )
    args = ap.parse_args()

    if args.budget is not None:
        print(
            f"note: --budget {args.budget} ignored; the parser sets thinking_budget itself\n"
        )

    audio_bytes = Path(args.audio).read_bytes()
    parser = GeminiAudioParser()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    sigs = Counter()
    elapsed_all = []

    for run_idx in range(1, args.runs + 1):
        t0 = time.perf_counter()
        tasks, usage = parser.parse_audio(audio_bytes, "audio/wav")
        elapsed = time.perf_counter() - t0
        elapsed_all.append(elapsed)

        sig = signature(tasks)
        sigs[sig] += 1

        record = {
            "run": run_idx,
            "model": "gemini-3.5-flash",
            "via": "GeminiAudioParser.parse_audio",
            "elapsed_sec": round(elapsed, 3),
            "tokens": usage,
            "tasks_count": len(tasks),
            "signature": sig,
            "tasks": tasks,
        }
        with log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")

        print(
            f"=== RUN {run_idx}/{args.runs}  ({elapsed:.2f}s, {usage['total']} tokens) ==="
        )
        for t in tasks:
            print(f"    [{t.get('lane')}/{t.get('class')}] {t.get('task')}")

    top_sig, top_n = sigs.most_common(1)[0]
    print(f"\n--- latency over {args.runs} runs ---")
    print(
        f"  p50 {statistics.median(elapsed_all):.2f}s   "
        f"min {min(elapsed_all):.2f}s   max {max(elapsed_all):.2f}s"
    )
    print("\n--- stability (count + lane + class) ---")
    for sig, n in sigs.most_common():
        print(f"  {n}/{args.runs}  {sig}")
    print(f"\nVERDICT: {top_n}/{args.runs} identical on count+lane+class")
    if top_n != args.runs:
        sys.exit(f"UNSTABLE: {len(sigs)} distinct shapes across {args.runs} runs")


if __name__ == "__main__":
    main()
