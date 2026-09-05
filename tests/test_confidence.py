import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.memory.confidence import compute_confidence


def test_single_observation_is_not_fully_confident():
    c = compute_confidence(1, 0)
    assert 0 < c < 0.7  # one observation should not be enough for high confidence


def test_confidence_rises_with_supporting_evidence():
    c1 = compute_confidence(1, 0)
    c2 = compute_confidence(2, 0)
    c3 = compute_confidence(5, 0)
    assert c1 < c2 < c3
    assert c3 < 1.0


def test_confidence_falls_with_conflicting_evidence():
    supported = compute_confidence(3, 0)
    conflicted = compute_confidence(3, 2)
    assert conflicted < supported


def test_equal_conflict_and_support_gives_low_confidence():
    c = compute_confidence(2, 2)
    assert c < 0.5
