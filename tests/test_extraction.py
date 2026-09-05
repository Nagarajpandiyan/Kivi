import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.memory.extraction import extract_candidates
from app.memory.validation import validate_candidate


def test_extracts_name_spelling_change():
    cands = extract_candidates("ask aditya to call me", "Ask Aaditya to call me.")
    assert len(cands) == 1
    assert cands[0].source_term == "aditya"
    assert cands[0].preferred_term == "Aaditya"


def test_ignores_pure_capitalization():
    cands = extract_candidates("ask aditya to call me", "Ask aditya to call me.")
    assert cands == [] or all(
        not validate_candidate(c).is_candidate for c in cands
    )


def test_ignores_pure_punctuation():
    v_candidates = extract_candidates("dont forget the meeting", "Don't forget the meeting.")
    for c in v_candidates:
        v = validate_candidate(c)
        assert not v.is_candidate, f"expected ordinary formatting rejection for {c}"


def test_accepts_kiwi_to_kivi():
    cands = extract_candidates(
        "ask aditya to review the sarvam kiwi service",
        "Ask Aditya to review the Sarvam Kivi service.",
    )
    kivi = [c for c in cands if c.source_term.lower() == "kiwi"]
    assert len(kivi) == 1
    v = validate_candidate(kivi[0])
    assert v.is_candidate
    assert v.is_common is True  # "kiwi" needs context to be applied later


def test_rejects_wildly_different_words():
    cands = extract_candidates("ask aditya about it", "Ask them regarding it.")
    for c in cands:
        v = validate_candidate(c)
        # "aditya" -> "them" should not be treated as a spelling preference
        if c.source_term.lower() == "aditya":
            assert not v.is_candidate


def test_no_candidates_when_texts_identical():
    assert extract_candidates("hello world", "hello world") == []
