"""
Formatting-process integration.

This is where retrieved memory actually changes the output, rather than
just being displayed next to it. We rebuild the formatted text token by
token; any token that matches an APPLY decision's source term is replaced
by the memory's preferred term, with the original token's capitalization
pattern applied to the replacement (so "aditya" -> "aaditya" but
"Aditya" -> "Aaditya", and "ADITYA" -> "AADITYA").

If a token already matches the *preferred* term (the formatter got it right
without help), it is left alone and no intervention is recorded for that
occurrence.
"""

import re

from app.decision.engine import Decision
from app.memory.extraction import normalize_token, tokenize

_WORD_RE = re.compile(r"^[A-Za-z0-9']+$")


def _match_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement.lower()


def apply_memory(formatted: str, decisions: list[Decision]) -> tuple[str, bool, list[str]]:
    """
    Returns (output_text, intervened, memory_ids_actually_used).
    `intervened` is True only if the text was actually changed -- a matched,
    APPLY-decided memory whose term was already spelled correctly does not
    count as an intervention.

    Handles both single-word memories ("aditya" -> "Aaditya") and
    multi-word memories ("open ai" -> "OpenAI") by matching the memory's
    source term against a run of consecutive tokens, longest term first so
    a 2-word term is not shadowed by a coincidental 1-word match.
    """
    apply_decisions = [d for d in decisions if d.decision == "APPLY"]
    if not apply_decisions:
        return formatted, False, []

    # Each decision's source term becomes a list of normalized word-tokens
    # (multi-word terms may include an internal space -> split it).
    term_specs = []
    for d in apply_decisions:
        words = [normalize_token(w) for w in d.source_term.split(" ")]
        words = [w for w in words if w]
        if words:
            term_specs.append((words, d))
    term_specs.sort(key=lambda spec: -len(spec[0]))  # longest term first

    tokens = tokenize(formatted)
    used_ids: list[str] = []
    intervened = False
    out_tokens: list[str] = []

    i = 0
    while i < len(tokens):
        matched_spec = None
        for words, decision in term_specs:
            n = len(words)
            if i + n > len(tokens):
                continue
            window = [normalize_token(tokens[i + k]) for k in range(n)]
            if window == words and all(_WORD_RE.match(tokens[i + k]) for k in range(n)):
                matched_spec = (words, decision, n)
                break
        if matched_spec:
            words, decision, n = matched_spec
            original_span = tokens[i:i + n]
            new_text = _match_case(original_span[0], decision.preferred_term)
            joined_original = " ".join(original_span)
            if new_text != joined_original:
                intervened = True
                used_ids.append(decision.memory_id)
            out_tokens.append(new_text)
            i += n
        else:
            out_tokens.append(tokens[i])
            i += 1

    output = ""
    for idx, tok in enumerate(out_tokens):
        if idx == 0:
            output += tok
        elif re.match(r"^[.,!?;:]$", tok):
            output += tok
        else:
            output += " " + tok
    return output, intervened, used_ids
