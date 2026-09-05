"""
Confidence.

confidence = supporting / (supporting + conflicting + K)

This is Laplace/add-one-style smoothing (K = LAPLACE_SMOOTHING_K, default 1.0):
- a single supporting observation gives confidence 1/(1+0+1) = 0.5 -- not
  enough on its own to leave CANDIDATE status (see lifecycle.py), which
  matches the "prefer conservative behaviour" guidance.
- confidence rises smoothly as consistent supporting evidence accumulates
  and drops sharply the moment conflicting evidence appears, which is what
  we want for a system that would rather abstain than over-correct.
- the value is always in [0, 1) and is simple enough to explain to a
  reviewer in one line, which matters because every decision must state a
  reason.

The exact thresholds that turn a confidence value into a lifecycle
transition live in config.py and are exercised by evaluation/.
"""

from app.config import LAPLACE_SMOOTHING_K


def compute_confidence(supporting: int, conflicting: int) -> float:
    return supporting / (supporting + conflicting + LAPLACE_SMOOTHING_K)
