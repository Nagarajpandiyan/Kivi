"""
Candidate validation.

A raw substitution found by extraction.py is not automatically a memory.
This module answers: "is this difference something Kivi's ordinary
formatter would do for anyone, or is it specific to this user's words?"

Rejected as ordinary formatting:
  - differs only by case            ("aditya" -> "Aditya")
  - differs only by punctuation      ("dont" -> "don't")
  - differs only by pluralization/whitespace of the same root
  - the two terms are wildly different words (large relative edit distance) --
    that is a grammar rewrite or ASR error unrelated to a personal term, not
    a spelling preference to remember.
  - the term is too short to be a meaningful personal term (e.g. single
    letters), since short-token diffs are usually formatting noise.

Accepted as a candidate:
  - the letters differ beyond case/punctuation (e.g. "aditya" -> "Aaditya",
    "kiwi" -> "Kivi") -- a genuine spelling/identity choice.
"""

import re
from dataclasses import dataclass

from app.common_words import is_common_word
from app.config import MAX_RELATIVE_EDIT_DISTANCE, MIN_TERM_LENGTH
from app.memory.extraction import RawCandidate, normalize_token


def _letters_only(s: str) -> str:
    """Strip ALL punctuation/apostrophes (not just leading/trailing) so that
    "dont" vs "don't" compare equal -- these differ only in punctuation, not
    in the letters spoken."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


@dataclass
class ValidationResult:
    is_candidate: bool
    reason: str
    memory_type: str | None = None
    is_common: bool = False


# A very small heuristic first-name list is enough to bias classification;
# it is not exhaustive and is not the source of truth for "is this a name"
# (evidence and confidence are). Purely a labeling nicety for the UI.
_LIKELY_NAME_HINTS = {
    "aditya", "aaditya", "aarav", "vivaan", "aryan", "krishna", "ishaan",
    "priya", "ananya", "diya", "kabir", "rohan", "sara", "meera", "arjun",
}


def classify_memory_type(source_norm: str, preferred_term: str) -> str:
    if source_norm in _LIKELY_NAME_HINTS:
        return "PERSON_NAME"
    if preferred_term[:1].isupper() and preferred_term.isalpha():
        # Capitalized single word Kivi doesn't otherwise recognize:
        # could be a name, product, or company -- default to the broadest
        # "user-specific term" bucket rather than guessing wrong.
        return "USER_SPECIFIC_TERM"
    return "SPELLING_VARIANT"


def validate_candidate(cand: RawCandidate) -> ValidationResult:
    source_norm = normalize_token(cand.source_term)
    preferred_norm = normalize_token(cand.preferred_term)

    if len(source_norm) < MIN_TERM_LENGTH or len(preferred_norm) < MIN_TERM_LENGTH:
        return ValidationResult(False, "Term too short to be a meaningful personal term.")

    is_multi_word = " " in source_norm or " " in preferred_norm
    if source_norm == preferred_norm:
        return ValidationResult(
            False, "Source and preferred terms are identical once case is normalized -- "
                   "this is ordinary formatting, not a memory."
        )
    if not is_multi_word and _letters_only(cand.source_term) == _letters_only(cand.preferred_term):
        return ValidationResult(
            False, "Source and preferred terms are identical once case and punctuation "
                   "are normalized -- this is ordinary formatting, not a memory."
        )

    max_len = max(len(source_norm), len(preferred_norm))
    dist = _levenshtein(source_norm, preferred_norm)
    if (dist / max_len) > MAX_RELATIVE_EDIT_DISTANCE:
        return ValidationResult(
            False, f"Terms differ too much ({dist}/{max_len} edits) to be a spelling "
                   "preference; likely an unrelated grammar rewrite or ASR error."
        )

    memory_type = classify_memory_type(source_norm, cand.preferred_term)
    common = is_common_word(source_norm)
    return ValidationResult(
        True,
        "Letters differ beyond case/punctuation -- candidate personal term.",
        memory_type=memory_type,
        is_common=common,
    )
