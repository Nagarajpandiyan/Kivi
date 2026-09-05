"""
Learning through ordinary use.

    observation (asr, formatted)
            |
            v
    candidate detection (extraction.py)
            |
            v
    candidate validation (validation.py)
            |
            v
    evidence (SUPPORTING / CONFLICTING) --------> memory_evidence rows
            |
            v
    confidence recompute (confidence.py)
            |
            v
    lifecycle transition:  CANDIDATE -> ACTIVE -> (UPDATED) -> DEACTIVATED

Timing decisions (documented, not assignment-mandated -- see config.py and
ARCHITECTURE.md):
  - ONE observation is never enough to become ACTIVE. It creates (or adds
    evidence to) a CANDIDATE. This is deliberate: a single ASR/formatting
    pair could be a one-off correction, not a standing preference.
  - A memory becomes ACTIVE once it has >= MIN_SUPPORTING_FOR_ACTIVE
    supporting observations AND confidence >= CONFIDENCE_ACTIVE_THRESHOLD.
  - Conflicting evidence (the same source term observed *without* the
    expected correction) immediately lowers confidence. If confidence on an
    ACTIVE memory falls below CONFIDENCE_DEACTIVATE_THRESHOLD, the memory is
    DEACTIVATED rather than silently kept around -- we would rather stop
    intervening than keep applying a correction the evidence no longer
    supports.
  - "UPDATED" marks a memory whose confidence changed on this observation
    (vs. freshly created); it does not overwrite `preferred_term` -- see
    "why we don't overwrite preferred_term" below.

Why we don't overwrite preferred_term on conflicting evidence: section 16 of
the brief warns against blindly overwriting a memory when evidence
conflicts. We keep the original preferred_term and let conflicting evidence
erode confidence (and eventually deactivate the memory) rather than flipping
the stored preference back and forth on every new observation.
"""

import json
import sqlite3
from dataclasses import dataclass, field

from app.config import (
    CONFIDENCE_ACTIVE_THRESHOLD,
    CONFIDENCE_DEACTIVATE_THRESHOLD,
    MIN_SUPPORTING_FOR_ACTIVE,
)
from app.db import ensure_user, new_id, now_iso, row_to_memory
from app.memory.confidence import compute_confidence
from app.memory.extraction import context_window, extract_candidates, normalize_token, tokenize
from app.memory.validation import validate_candidate

MAX_CONTEXT_TOKENS = 12


@dataclass
class LearnResult:
    candidates_found: int = 0
    candidates_rejected: list[dict] = field(default_factory=list)
    evidence_created: list[dict] = field(default_factory=list)
    memories_created: list[dict] = field(default_factory=list)
    memories_updated: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "candidates_found": self.candidates_found,
            "candidates_rejected": self.candidates_rejected,
            "evidence_created": self.evidence_created,
            "memories_created": self.memories_created,
            "memories_updated": self.memories_updated,
        }


def _get_memory_by_source(conn: sqlite3.Connection, user_id: str, normalized_source: str):
    row = conn.execute(
        "SELECT * FROM memories WHERE user_id = ? AND normalized_source = ?",
        (user_id, normalized_source),
    ).fetchone()
    return row_to_memory(row) if row else None


def _apply_lifecycle(mem: dict) -> str:
    """Return the new status for `mem` given its current counts/confidence."""
    supporting = mem["supporting_evidence_count"]
    conflicting = mem["conflicting_evidence_count"]
    confidence = mem["confidence"]

    if mem["status"] in ("ACTIVE", "UPDATED"):
        if confidence < CONFIDENCE_DEACTIVATE_THRESHOLD:
            return "DEACTIVATED"
        return "UPDATED"

    if mem["status"] == "CANDIDATE":
        if supporting >= MIN_SUPPORTING_FOR_ACTIVE and confidence >= CONFIDENCE_ACTIVE_THRESHOLD:
            return "ACTIVE"
        return "CANDIDATE"

    return mem["status"]  # DEACTIVATED stays DEACTIVATED unless explicitly reactivated


def _merge_context(existing: list[str], new_tokens: list[str]) -> list[str]:
    merged = list(dict.fromkeys(existing + new_tokens))  # de-dupe, preserve order
    return merged[-MAX_CONTEXT_TOKENS:]


def _record_evidence(conn, memory_id: str, asr: str, formatted: str, evidence_type: str, source_id: str | None):
    ev_id = new_id("ev")
    conn.execute(
        "INSERT INTO memory_evidence (id, memory_id, asr_text, formatted_text, evidence_type, source_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ev_id, memory_id, asr, formatted, evidence_type, source_id, now_iso()),
    )
    return ev_id


def learn(conn: sqlite3.Connection, user_id: str, asr: str, formatted: str, source_id: str | None = None) -> LearnResult:
    ensure_user(conn, user_id)
    result = LearnResult()

    asr_tokens = tokenize(asr)
    fmt_tokens = tokenize(formatted)
    asr_norm_tokens = [normalize_token(t) for t in asr_tokens]

    # 1) Conflicting evidence: an existing memory's source term appears in
    #    this ASR text, unchanged, in the formatted text (no correction
    #    applied where our memory says one should have been).
    touched_memory_ids: set[str] = set()
    for idx, tok_norm in enumerate(asr_norm_tokens):
        if not tok_norm:
            continue
        mem = _get_memory_by_source(conn, user_id, tok_norm)
        if not mem or mem["status"] == "DEACTIVATED":
            continue
        # If this index was part of a 'replace' opcode it will be handled
        # below as supporting/competing evidence instead.
        if idx < len(fmt_tokens) and normalize_token(fmt_tokens[idx]) == tok_norm and tok_norm != normalize_token(mem["preferred_term"]):
            _record_evidence(conn, mem["id"], asr, formatted, "CONFLICTING", source_id)
            conn.execute(
                "UPDATE memories SET conflicting_evidence_count = conflicting_evidence_count + 1, updated_at = ? WHERE id = ?",
                (now_iso(), mem["id"]),
            )
            touched_memory_ids.add(mem["id"])

    # 2) Candidate substitutions found by diffing ASR vs formatted.
    raw_candidates = extract_candidates(asr, formatted)
    result.candidates_found = len(raw_candidates)

    for cand in raw_candidates:
        validation = validate_candidate(cand)
        if not validation.is_candidate:
            result.candidates_rejected.append(
                {"source_term": cand.source_term, "preferred_term": cand.preferred_term, "reason": validation.reason}
            )
            continue

        source_norm = normalize_token(cand.source_term)
        preferred_norm = normalize_token(cand.preferred_term)
        ctx = context_window(asr_tokens, cand.asr_index)

        existing = _get_memory_by_source(conn, user_id, source_norm)

        if existing is None:
            mem_id = new_id("mem")
            confidence = compute_confidence(1, 0)
            conn.execute(
                "INSERT INTO memories (id, user_id, source_term, preferred_term, normalized_source, memory_type, "
                "status, confidence, supporting_evidence_count, conflicting_evidence_count, context_tokens, "
                "is_common_word, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    mem_id, user_id, cand.source_term, cand.preferred_term, source_norm, validation.memory_type,
                    "CANDIDATE", confidence, 1, 0, json.dumps(ctx), int(validation.is_common), now_iso(), now_iso(),
                ),
            )
            _record_evidence(conn, mem_id, asr, formatted, "SUPPORTING", source_id)
            new_row = row_to_memory(conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone())
            new_status = _apply_lifecycle(new_row)
            conn.execute("UPDATE memories SET status = ? WHERE id = ?", (new_status, mem_id))
            new_row["status"] = new_status
            result.memories_created.append(new_row)
            result.evidence_created.append({"memory_id": mem_id, "type": "SUPPORTING"})
            continue

        if existing["status"] == "DEACTIVATED":
            # A deactivated memory does not silently reactivate from new
            # evidence alone; it stays inert until explicitly reactivated
            # or a fresh CANDIDATE naturally re-forms. We still log the
            # observation for provenance.
            result.candidates_rejected.append(
                {"source_term": cand.source_term, "preferred_term": cand.preferred_term,
                 "reason": "A memory for this term was previously deactivated; not auto-reactivating."}
            )
            continue

        evidence_type = "SUPPORTING" if preferred_norm == normalize_token(existing["preferred_term"]) else "CONFLICTING"
        _record_evidence(conn, existing["id"], asr, formatted, evidence_type, source_id)
        if evidence_type == "SUPPORTING":
            conn.execute(
                "UPDATE memories SET supporting_evidence_count = supporting_evidence_count + 1, "
                "context_tokens = ?, updated_at = ? WHERE id = ?",
                (json.dumps(_merge_context(existing["context_tokens"], ctx)), now_iso(), existing["id"]),
            )
        else:
            conn.execute(
                "UPDATE memories SET conflicting_evidence_count = conflicting_evidence_count + 1, updated_at = ? WHERE id = ?",
                (now_iso(), existing["id"]),
            )
        touched_memory_ids.add(existing["id"])

    # 3) Recompute confidence + lifecycle for every memory touched this call.
    for mem_id in touched_memory_ids:
        row = row_to_memory(conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,)).fetchone())
        new_conf = compute_confidence(row["supporting_evidence_count"], row["conflicting_evidence_count"])
        row["confidence"] = new_conf
        new_status = _apply_lifecycle(row)
        conn.execute(
            "UPDATE memories SET confidence = ?, status = ?, updated_at = ? WHERE id = ?",
            (new_conf, new_status, now_iso(), mem_id),
        )
        row["status"] = new_status
        result.memories_updated.append(row)

    return result
