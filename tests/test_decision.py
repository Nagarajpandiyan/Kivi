import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.decision.engine import decide


def make_memory(**overrides):
    base = dict(
        id="mem_1", source_term="aditya", preferred_term="Aaditya",
        memory_type="PERSON_NAME", status="ACTIVE", confidence=0.9,
        supporting_evidence_count=3, conflicting_evidence_count=0,
        context_tokens=[], is_common_word=False,
    )
    base.update(overrides)
    return base


def test_candidate_status_is_ignored():
    d = decide(make_memory(status="CANDIDATE", confidence=0.9), "ask aditya", "Ask Aditya")
    assert d.decision == "IGNORE"
    assert "status is CANDIDATE" in d.reason


def test_low_confidence_is_ignored():
    d = decide(make_memory(confidence=0.3), "ask aditya", "Ask Aditya")
    assert d.decision == "IGNORE"


def test_high_confidence_non_common_word_applies():
    d = decide(make_memory(), "ask aditya", "Ask Aditya")
    assert d.decision == "APPLY"


def test_common_word_without_context_is_ignored():
    mem = make_memory(source_term="kiwi", preferred_term="Kivi", is_common_word=True,
                       context_tokens=["sarvam", "service"])
    d = decide(mem, "i ate a kiwi", "I ate a kiwi.")
    assert d.decision == "IGNORE"
    assert "ordinary word" in d.reason


def test_common_word_with_context_applies():
    mem = make_memory(source_term="kiwi", preferred_term="Kivi", is_common_word=True,
                       context_tokens=["sarvam", "service"])
    d = decide(mem, "review the sarvam kiwi service", "Review the Sarvam Kiwi service.")
    assert d.decision == "APPLY"


def test_heavy_conflict_is_ignored():
    mem = make_memory(supporting_evidence_count=2, conflicting_evidence_count=3, confidence=0.7)
    d = decide(mem, "ask aditya", "Ask Aditya")
    assert d.decision == "IGNORE"
