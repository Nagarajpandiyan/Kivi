"""
Candidate extraction.

Given (asr, formatted), find the word-level substitutions that turned the
raw ASR text into the formatted text, then decide which of those
substitutions are *candidates* for personal memory (as opposed to ordinary
capitalization, punctuation, or grammar that Kivi's formatter would apply
to anyone).

Approach: tokenize both strings, align them with difflib.SequenceMatcher
over a punctuation/case-normalized view of the tokens (so "aditya" lines up
with "Aditya."), then inspect each 'replace' block. This is intentionally a
straightforward word-alignment diff rather than a phonetic/embedding
model -- it is enough to reliably recover the substitutions in the assignment's
transcripts, is fully deterministic, and is easy for a reviewer to audit.
"""

import difflib
import re
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[A-Za-z0-9']+|[^\sA-Za-z0-9']")


def tokenize(text: str) -> list[str]:
    """Word + punctuation tokens, order-preserving."""
    return _TOKEN_RE.findall(text)


def normalize_token(tok: str) -> str:
    """Lowercase, strip surrounding punctuation -- used only for alignment."""
    return tok.lower().strip(".,!?;:'\"-")


@dataclass
class RawCandidate:
    source_term: str       # term as spoken (from ASR)
    preferred_term: str    # term as formatted (what Kivi should have produced)
    asr_index: int          # token index in ASR, for context extraction
    formatted_index: int    # token index in formatted text


def extract_candidates(asr: str, formatted: str) -> list[RawCandidate]:
    asr_tokens = tokenize(asr)
    fmt_tokens = tokenize(formatted)

    asr_norm = [normalize_token(t) for t in asr_tokens]
    fmt_norm = [normalize_token(t) for t in fmt_tokens]

    sm = difflib.SequenceMatcher(a=asr_norm, b=fmt_norm, autojunk=False)
    candidates: list[RawCandidate] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "replace":
            continue  # 'equal' = no change; 'insert'/'delete' = pure formatting, not a term substitution
        # Only consider aligned single-word-for-single-word (or small n:n) swaps.
        # Larger blocks are usually grammar rewrites, not personal terms.
        a_len, b_len = i2 - i1, j2 - j1
        if a_len == 0 or b_len == 0 or a_len > 3 or b_len > 3:
            continue

        # Trim leading/trailing tokens that are pure punctuation (e.g. a
        # trailing "." that only got swept into this block because the ASR
        # side has no sentence-final punctuation to align against). Only
        # the letter-bearing tokens are a real term substitution.
        aj1, aj2, bj1, bj2 = i1, i2, j1, j2
        while aj1 < aj2 and not re.search(r"[A-Za-z]", asr_tokens[aj1]):
            aj1 += 1
        while aj2 > aj1 and not re.search(r"[A-Za-z]", asr_tokens[aj2 - 1]):
            aj2 -= 1
        while bj1 < bj2 and not re.search(r"[A-Za-z]", fmt_tokens[bj1]):
            bj1 += 1
        while bj2 > bj1 and not re.search(r"[A-Za-z]", fmt_tokens[bj2 - 1]):
            bj2 -= 1

        source_term = " ".join(asr_tokens[aj1:aj2]).strip()
        preferred_term = " ".join(fmt_tokens[bj1:bj2]).strip()
        if not source_term or not preferred_term:
            continue
        candidates.append(
            RawCandidate(
                source_term=source_term,
                preferred_term=preferred_term,
                asr_index=aj1,
                formatted_index=bj1,
            )
        )
    return candidates


def context_window(tokens: list[str], index: int, radius: int = 3) -> list[str]:
    """Normalized neighboring tokens around `index`, used as memory context.
    Generic/filler words are excluded (see common_words.is_context_noise) so
    that only distinguishing terms count toward the relevance check."""
    from app.common_words import is_context_noise

    lo, hi = max(0, index - radius), min(len(tokens), index + radius + 1)
    out = []
    for i in range(lo, hi):
        if i == index:
            continue
        n = normalize_token(tokens[i])
        if n and re.search(r"[a-z]", n) and not is_context_noise(n):
            out.append(n)
    return out
