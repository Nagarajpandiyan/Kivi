"""
Decision engine.

For each memory retrieved for this request, decide APPLY or IGNORE, and
state why. This is the layer that keeps Kivi from blindly rewriting every
matching word -- it is where "deliberately do nothing" lives.

Checks, in order (first failing check determines the IGNORE reason):
  1. status must be ACTIVE/UPDATED. A CANDIDATE hasn't earned enough evidence
     yet to influence output.
  2. confidence must be >= CONFIDENCE_APPLY_THRESHOLD.
  3. conflicting evidence must not dominate supporting evidence (belt-and-
     braces on top of confidence, kept as its own explainable check).
  4. if the memory's source term is an ordinary dictionary word (e.g.
     "kiwi"), the current input must share at least one context token with
     the memory's stored context (e.g. "sarvam"), or we abstain -- the word
     is genuinely ambiguous without it ("I ate a kiwi yesterday" has no
     such context and should NOT become "I ate a Kivi yesterday").

Anything that passes all four checks is APPLY.
"""

from dataclasses import dataclass

from app.config import CONFIDENCE_APPLY_THRESHOLD
from app.memory.extraction import normalize_token, tokenize


@dataclass
class Decision:
    memory_id: str
    decision: str  # APPLY | IGNORE
    confidence: float
    reason: str
    source_term: str
    preferred_term: str


def decide(memory: dict, asr: str, formatted: str) -> Decision:
    base = dict(memory_id=memory["id"], confidence=memory["confidence"],
                source_term=memory["source_term"], preferred_term=memory["preferred_term"])

    if memory["status"] not in ("ACTIVE", "UPDATED"):
        return Decision(**base, decision="IGNORE",
                         reason=f"Memory status is {memory['status']}; not enough evidence yet to intervene.")

    if memory["confidence"] < CONFIDENCE_APPLY_THRESHOLD:
        return Decision(**base, decision="IGNORE",
                         reason=f"Confidence {memory['confidence']:.2f} is below the "
                                f"apply threshold ({CONFIDENCE_APPLY_THRESHOLD:.2f}).")

    if memory["conflicting_evidence_count"] >= memory["supporting_evidence_count"]:
        return Decision(**base, decision="IGNORE",
                         reason="Conflicting evidence is as frequent as supporting evidence; abstaining.")

    if memory["is_common_word"]:
        input_tokens = set(normalize_token(t) for t in tokenize(asr) + tokenize(formatted))
        input_tokens.discard(normalize_token(memory["source_term"]))
        input_tokens.discard("")
        context = set(memory["context_tokens"])
        if not (input_tokens & context):
            return Decision(
                **base, decision="IGNORE",
                reason=(f"'{memory['source_term']}' is an ordinary word and this input shares none of the "
                        f"context ({sorted(context)}) previously associated with the personal meaning; "
                        "treating it as its ordinary sense."),
            )

    return Decision(**base, decision="APPLY",
                     reason=f"Active, high-confidence ({memory['confidence']:.2f}) personal term matched in context.")


def decide_all(memories: list[dict], asr: str, formatted: str) -> list[Decision]:
    return [decide(m, asr, formatted) for m in memories]
