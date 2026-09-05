"""
Reproducible evaluation.

Runs every case in data/evaluation/dataset.jsonl against an ISOLATED SQLite
database (never the interactive demo's database), replays each case's
learning_observations, processes its test (asr, formatted) request, and
compares the actual output/decision against what the case expects.

Usage (see RUN.md for the exact commands):
    python -m evaluation.runner

Writes:
    evaluation/results/results.json   -- one record per case
    evaluation/results/metrics.json   -- aggregate + per-category metrics
    evaluation/results/report.md      -- human-readable report incl. failures
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Isolate: point the backend at a throwaway DB file BEFORE importing app.*
_eval_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["KIVI_DB_PATH"] = _eval_db.name

from app.db import apply_migrations, get_conn, new_id, now_iso, reset_all, row_to_memory  # noqa: E402
from app.decision.engine import decide_all  # noqa: E402
from app.formatter.format import apply_memory  # noqa: E402
from app.memory.lifecycle import learn  # noqa: E402
from app.retrieval.retrieve import retrieve_relevant_memories  # noqa: E402

DATASET = ROOT / "data" / "evaluation" / "dataset.jsonl"
RESULTS_DIR = ROOT / "evaluation" / "results"


def load_cases():
    if not DATASET.exists():
        print(f"No dataset at {DATASET}. Run: python evaluation/generate_dataset.py")
        sys.exit(1)
    with open(DATASET) as f:
        return [json.loads(line) for line in f if line.strip()]


def process(conn, user_id, asr, formatted):
    memories = retrieve_relevant_memories(conn, user_id, asr, formatted)
    decisions = decide_all(memories, asr, formatted)
    output, intervened, used_ids = apply_memory(formatted, decisions)
    return output, ("APPLY" if intervened else "IGNORE"), decisions, memories


def run():
    apply_migrations()
    reset_all()
    cases = load_cases()

    db_size_before = os.path.getsize(_eval_db.name) if os.path.exists(_eval_db.name) else 0

    results = []
    for case in cases:
        user_id = case["user_id"]

        t0 = time.perf_counter()
        with get_conn() as conn:
            for obs in case["learning_observations"]:
                learn(conn, user_id, obs["asr"], obs["formatted"])

            if case["category"] == "deactivated_memory_no_apply":
                rows = conn.execute(
                    "SELECT id FROM memories WHERE user_id = ? AND status != 'DEACTIVATED'", (user_id,)
                ).fetchall()
                for r in rows:
                    conn.execute("UPDATE memories SET status = 'DEACTIVATED' WHERE id = ?", (r["id"],))

            output, decision, decisions, retrieved = process(conn, user_id, case["asr"], case["formatted"])

            # Persist decision records too, exactly like the API route does,
            # so the evaluation's database growth and inspectability match
            # what real traffic through /transcript/process would produce.
            for d in decisions:
                conn.execute(
                    "INSERT INTO memory_decisions (id, memory_id, user_id, input_asr, input_formatted, decision, "
                    "confidence, reason, output_text, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (new_id("dec"), d.memory_id, user_id, case["asr"], case["formatted"], d.decision,
                     d.confidence, d.reason, output, now_iso()),
                )
            if not decisions:
                conn.execute(
                    "INSERT INTO memory_decisions (id, memory_id, user_id, input_asr, input_formatted, decision, "
                    "confidence, reason, output_text, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (new_id("dec"), None, user_id, case["asr"], case["formatted"], "IGNORE",
                     None, "No stored memory's source term appears in this input.", output, now_iso()),
                )
        latency_ms = (time.perf_counter() - t0) * 1000

        with get_conn() as conn:
            mem_rows = conn.execute("SELECT * FROM memories WHERE user_id = ?", (user_id,)).fetchall()
            memory_state = [row_to_memory(r) for r in mem_rows]

        passed = (output == case["expected_output"]) and (decision == case["expected_decision"])
        results.append({
            "id": case["id"],
            "category": case["category"],
            "user_id": user_id,
            "asr": case["asr"],
            "formatted": case["formatted"],
            "expected_output": case["expected_output"],
            "actual_output": output,
            "expected_decision": case["expected_decision"],
            "actual_decision": decision,
            "pass": passed,
            "latency_ms": round(latency_ms, 3),
            "memory_state": memory_state,
            "decisions": [d.__dict__ for d in decisions],
            "case_reason": case["reason"],
        })

    return results


def compute_db_growth():
    with get_conn() as conn:
        counts = {}
        for table in ("users", "memories", "memory_evidence", "memory_decisions"):
            counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    size_bytes = os.path.getsize(_eval_db.name) if os.path.exists(_eval_db.name) else 0
    return {"row_counts": counts, "db_file_size_bytes": size_bytes}


def compute_metrics(results, db_growth=None):
    total = len(results)
    passed = sum(r["pass"] for r in results)

    by_category = {}
    for r in results:
        c = by_category.setdefault(r["category"], {"total": 0, "passed": 0})
        c["total"] += 1
        c["passed"] += int(r["pass"])
    for c in by_category.values():
        c["accuracy"] = round(c["passed"] / c["total"], 3) if c["total"] else None

    should_apply = [r for r in results if r["expected_decision"] == "APPLY"]
    should_ignore = [r for r in results if r["expected_decision"] == "IGNORE"]

    def rate(rows, predicate):
        return round(sum(predicate(r) for r in rows) / len(rows), 3) if rows else None

    useful_intervention_rate = rate(should_apply, lambda r: r["actual_decision"] == "APPLY")
    unnecessary_intervention_rate = rate(should_ignore, lambda r: r["actual_decision"] == "APPLY")
    incorrect_intervention_rate = rate(
        should_apply, lambda r: r["actual_decision"] == "APPLY" and r["actual_output"] != r["expected_output"]
    )
    correct_abstention_rate = rate(should_ignore, lambda r: r["actual_decision"] == "IGNORE")

    latencies = [r["latency_ms"] for r in results]
    return {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "output_accuracy": round(passed / total, 3) if total else None,
        "by_category": by_category,
        "useful_intervention_rate": useful_intervention_rate,
        "unnecessary_intervention_rate": unnecessary_intervention_rate,
        "incorrect_intervention_rate": incorrect_intervention_rate,
        "correct_abstention_rate": correct_abstention_rate,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "max": round(max(latencies), 3) if latencies else None,
            "min": round(min(latencies), 3) if latencies else None,
        },
        "model_calls": 0,
        "estimated_cost_usd": 0.0,
        "database_growth": db_growth or {},
        "note": "No LLM calls are made anywhere in this pipeline; the memory engine is fully deterministic (see ARCHITECTURE.md, section 'AI/LLM usage').",
    }


def write_report(results, metrics):
    lines = ["# Kivi memory evaluation report", ""]
    lines.append(f"Generated by `python -m evaluation.runner`. {metrics['total_cases']} cases, "
                 f"{metrics['passed']} passed, {metrics['failed']} failed "
                 f"(output accuracy: {metrics['output_accuracy']}).")
    lines.append("")
    lines.append("## Aggregate metrics")
    lines.append(f"- Useful intervention rate (should APPLY and did): {metrics['useful_intervention_rate']}")
    lines.append(f"- Unnecessary intervention rate (should IGNORE but APPLIED): {metrics['unnecessary_intervention_rate']}")
    lines.append(f"- Incorrect intervention rate (APPLIED but wrong output): {metrics['incorrect_intervention_rate']}")
    lines.append(f"- Correct abstention rate (should IGNORE and did): {metrics['correct_abstention_rate']}")
    lines.append(f"- Latency: mean {metrics['latency_ms']['mean']}ms, max {metrics['latency_ms']['max']}ms")
    lines.append(f"- Model calls: {metrics['model_calls']} (deterministic pipeline, no LLM)")
    dg = metrics.get("database_growth", {})
    if dg:
        lines.append(f"- Database growth after this run: {dg.get('row_counts')} "
                     f"(SQLite file: {dg.get('db_file_size_bytes')} bytes)")
    lines.append("")
    lines.append("## By category")
    lines.append("")
    lines.append("| category | passed | total | accuracy |")
    lines.append("|---|---|---|---|")
    for cat, c in sorted(metrics["by_category"].items()):
        lines.append(f"| {cat} | {c['passed']} | {c['total']} | {c['accuracy']} |")
    lines.append("")

    failures = [r for r in results if not r["pass"]]
    lines.append(f"## Failures ({len(failures)})")
    lines.append("")
    if not failures:
        lines.append("None.")
    for r in failures:
        lines.append(f"### {r['id']} ({r['category']})")
        lines.append(f"- Input: `{r['asr']}` / `{r['formatted']}`")
        lines.append(f"- Expected: decision=`{r['expected_decision']}`, output=`{r['expected_output']}`")
        lines.append(f"- Actual: decision=`{r['actual_decision']}`, output=`{r['actual_output']}`")
        lines.append(f"- Case rationale: {r['case_reason']}")
        for d in r["decisions"]:
            lines.append(f"  - decision on memory `{d.get('source_term')}`: {d.get('decision')} "
                         f"(confidence={d.get('confidence')}) -- {d.get('reason')}")
        lines.append("")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "report.md").write_text("\n".join(lines))


def main():
    results = run()
    db_growth = compute_db_growth()
    metrics = compute_metrics(results, db_growth)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "results.json").write_text(json.dumps(results, indent=2, default=str))
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    write_report(results, metrics)

    print(f"{metrics['passed']}/{metrics['total_cases']} passed "
          f"(output accuracy {metrics['output_accuracy']})")
    print(f"Results written to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
