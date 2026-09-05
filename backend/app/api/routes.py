from fastapi import APIRouter, HTTPException, Query

from app.db import get_conn, new_id, now_iso, reset_all, row_to_memory
from app.decision.engine import decide_all
from app.formatter.format import apply_memory
from app.memory.lifecycle import learn as learn_fn
from app.retrieval.retrieve import retrieve_relevant_memories
from app.schemas import ImportItem, LearnRequest, ProcessRequest

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/memory/learn")
def memory_learn(req: LearnRequest):
    with get_conn() as conn:
        result = learn_fn(conn, req.user_id, req.asr, req.formatted, req.source_id)
    return result.as_dict()


@router.get("/memory")
def memory_list(user_id: str = Query("user_1"), status: str | None = None):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM memories WHERE user_id = ? AND status = ? ORDER BY updated_at DESC",
                (user_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
            ).fetchall()
        return [row_to_memory(r) for r in rows]


@router.get("/memory/{memory_id}")
def memory_detail(memory_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            raise HTTPException(404, "memory not found")
        mem = row_to_memory(row)
        evidence = conn.execute(
            "SELECT * FROM memory_evidence WHERE memory_id = ? ORDER BY created_at", (memory_id,)
        ).fetchall()
        decisions = conn.execute(
            "SELECT * FROM memory_decisions WHERE memory_id = ? ORDER BY created_at DESC", (memory_id,)
        ).fetchall()
        mem["evidence"] = [dict(e) for e in evidence]
        mem["decisions"] = [dict(d) for d in decisions]
        return mem


@router.post("/memory/{memory_id}/deactivate")
def memory_deactivate(memory_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            raise HTTPException(404, "memory not found")
        conn.execute(
            "UPDATE memories SET status = 'DEACTIVATED', updated_at = ? WHERE id = ?",
            (now_iso(), memory_id),
        )
    return {"id": memory_id, "status": "DEACTIVATED"}


@router.post("/transcript/process")
def transcript_process(req: ProcessRequest):
    with get_conn() as conn:
        candidates = retrieve_relevant_memories(conn, req.user_id, req.asr, req.formatted)
        decisions = decide_all(candidates, req.asr, req.formatted)
        output, intervened, used_ids = apply_memory(req.formatted, decisions)

        decision_records = []
        for d in decisions:
            dec_id = new_id("dec")
            conn.execute(
                "INSERT INTO memory_decisions (id, memory_id, user_id, input_asr, input_formatted, decision, "
                "confidence, reason, output_text, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (dec_id, d.memory_id, req.user_id, req.asr, req.formatted, d.decision, d.confidence, d.reason, output, now_iso()),
            )
            decision_records.append({"id": dec_id, **d.__dict__})

        if not decisions:
            dec_id = new_id("dec")
            reason = "No stored memory's source term appears in this input."
            conn.execute(
                "INSERT INTO memory_decisions (id, memory_id, user_id, input_asr, input_formatted, decision, "
                "confidence, reason, output_text, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (dec_id, None, req.user_id, req.asr, req.formatted, "IGNORE", None, reason, output, now_iso()),
            )
            decision_records.append({"id": dec_id, "memory_id": None, "decision": "IGNORE",
                                      "confidence": None, "reason": reason})

    apply_records = [d for d in decision_records if d["decision"] == "APPLY"]
    if apply_records:
        top_reason = "; ".join(d["reason"] for d in apply_records)
    elif decision_records:
        top_reason = "; ".join(d["reason"] for d in decision_records)
    else:
        top_reason = "No memory retrieved."
    return {
        "output": output,
        "decision": "APPLY" if intervened else "IGNORE",
        "intervened": intervened,
        "memories_used": used_ids,
        "decisions": decision_records,
        "reason": top_reason,
    }


@router.get("/decisions/{decision_id}")
def decision_detail(decision_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM memory_decisions WHERE id = ?", (decision_id,)).fetchone()
        if not row:
            raise HTTPException(404, "decision not found")
        return dict(row)


@router.post("/import")
def import_observations(items: list[ImportItem]):
    created, updated = 0, 0
    with get_conn() as conn:
        for item in items:
            result = learn_fn(conn, item.user_id, item.asr, item.formatted, item.source_id)
            created += len(result.memories_created)
            updated += len(result.memories_updated)
    return {"observations_imported": len(items), "memories_created": created, "memories_updated": updated}


@router.post("/reset")
def reset():
    reset_all()
    return {"status": "reset"}
