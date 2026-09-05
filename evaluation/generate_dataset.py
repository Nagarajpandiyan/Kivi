"""
Builds data/evaluation/dataset.jsonl: a varied, reproducible set of cases
that exercise the pipeline beyond the single Aditya/Kivi example given in
the brief.

Each case is self-contained: it gets its own user_id (so cases never
pollute each other's memory, even though they all run against the same
database in one evaluation pass), a list of learning_observations to
replay first, then one (asr, formatted) request to process, plus what we
expect to happen and why.

This dataset size (see CASE COUNT at the bottom) is an engineering choice,
not a Sarvam requirement -- see ASSIGNMENT_NOTES.md.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "evaluation" / "dataset.jsonl"

cases = []
_next_id = 1


def add(category, learning_observations, asr, formatted, expected_output, expected_decision, reason):
    global _next_id
    case_id = f"case_{_next_id:03d}"
    _next_id += 1
    cases.append({
        "id": case_id,
        "user_id": f"eval_{case_id}",
        "category": category,
        "learning_observations": learning_observations,
        "asr": asr,
        "formatted": formatted,
        "expected_output": expected_output,
        "expected_decision": expected_decision,
        "reason": reason,
    })


# ---------------------------------------------------------------------------
# 1) POSITIVE: name spelling corrections learned from 2+ observations, then
#    correctly applied to an unseen sentence.
# ---------------------------------------------------------------------------
name_pairs = [
    ("aditya", "Aaditya"), ("priya", "Priyaa"), ("rohan", "Rohaan"),
    ("sara", "Saraah"), ("arjun", "Arjunn"), ("meera", "Meira"),
    ("kabir", "Qabir"), ("ishaan", "Ishaanh"), ("diya", "Diyaa"), ("vivaan", "Vivaanh"),
]
templates = [
    ("ask {n} to call me", "Ask {N} to call me."),
    ("meet {n} tomorrow", "Meet {N} tomorrow."),
    ("email {n} the report", "Email {N} the report."),
    ("tell {n} about the change", "Tell {N} about the change."),
]
test_templates = [
    ("ask {n} about the meeting", "Ask {n_cap} about the meeting."),
    ("call {n} now", "Call {n_cap} now."),
    ("remind {n} tonight", "Remind {n_cap} tonight."),
]
for i, (src, pref) in enumerate(name_pairs):
    obs = []
    for j in range(2):
        a_t, f_t = templates[j % len(templates)]
        obs.append({"asr": a_t.format(n=src), "formatted": f_t.format(N=pref)})
    t_a, t_f = test_templates[i % len(test_templates)]
    asr = t_a.format(n=src)
    formatted = t_f.format(n_cap=src.capitalize())
    expected = t_f.format(n_cap=pref)
    add("positive_apply", obs, asr, formatted, expected, "APPLY",
        f"Two consistent supporting observations should make '{src}'->'{pref}' ACTIVE and applicable.")

# ---------------------------------------------------------------------------
# 2) ABSTENTION: common-word product/company term without supporting context
#    should NOT be corrected, even though a memory exists.
# ---------------------------------------------------------------------------
common_word_terms = [
    ("kiwi", "Kivi", "sarvam", "ate a kiwi yesterday", "I ate a kiwi yesterday."),
    ("current", "Currint", "billing", "check the current balance", "Check the current balance."),
    ("orange", "Orenj", "design", "the sky turned orange", "The sky turned orange."),
]
for src, pref, ctx_word, irrelevant_asr, irrelevant_formatted in common_word_terms:
    obs = [
        {"asr": f"ask about the {ctx_word} {src} service", "formatted": f"Ask about the {ctx_word.capitalize()} {pref} service."},
        {"asr": f"check the {ctx_word} {src} release", "formatted": f"Check the {ctx_word.capitalize()} {pref} release."},
    ]
    add("correct_abstention_common_word", obs, irrelevant_asr, irrelevant_formatted, irrelevant_formatted, "IGNORE",
        f"'{src}' is an ordinary word; without '{ctx_word}' present, Kivi must not force the personal spelling.")

# ---------------------------------------------------------------------------
# 3) Same common-word terms, but WITH the supporting context -> should APPLY.
# ---------------------------------------------------------------------------
for src, pref, ctx_word, _, _ in common_word_terms:
    obs = [
        {"asr": f"ask about the {ctx_word} {src} service", "formatted": f"Ask about the {ctx_word.capitalize()} {pref} service."},
        {"asr": f"check the {ctx_word} {src} release", "formatted": f"Check the {ctx_word.capitalize()} {pref} release."},
    ]
    asr = f"review the {ctx_word} {src} docs"
    formatted = f"Review the {ctx_word.capitalize()} {src.capitalize()} docs."
    expected = f"Review the {ctx_word.capitalize()} {pref} docs."
    add("useful_intervention_with_context", obs, asr, formatted, expected, "APPLY",
        f"'{ctx_word}' context present alongside '{src}' should trigger the learned correction.")

# ---------------------------------------------------------------------------
# 4) WEAK EVIDENCE: a single observation should stay CANDIDATE and NOT apply.
# ---------------------------------------------------------------------------
weak_pairs = [("nitin", "Niteen"), ("farah", "Faraah"), ("omkar", "Aumkar")]
for src, pref in weak_pairs:
    obs = [{"asr": f"ask {src} to join", "formatted": f"Ask {pref} to join."}]
    asr = f"call {src} later"
    formatted = f"Call {src.capitalize()} later."
    add("weak_evidence_no_apply", obs, asr, formatted, formatted, "IGNORE",
        "A single supporting observation is insufficient evidence; the memory stays CANDIDATE.")

# ---------------------------------------------------------------------------
# 5) CONFLICTING EVIDENCE: alternating corrections should suppress confidence
#    enough that Kivi abstains.
# ---------------------------------------------------------------------------
conflict_pairs = [("veer", "Vheer"), ("naina", "Nainah")]
for src, pref in conflict_pairs:
    obs = [
        {"asr": f"ask {src} to review", "formatted": f"Ask {pref} to review."},
        {"asr": f"tell {src} directly", "formatted": f"Tell {src.capitalize()} directly."},  # conflicting: no correction applied
        {"asr": f"meet {src} soon", "formatted": f"Meet {pref} soon."},
    ]
    asr = f"call {src} today"
    formatted = f"Call {src.capitalize()} today."
    add("conflicting_evidence_abstain", obs, asr, formatted, formatted, "IGNORE",
        "Conflicting evidence lowers confidence below the apply threshold; Kivi abstains rather than guessing.")

# ---------------------------------------------------------------------------
# 6) ORDINARY FORMATTING: capitalization/punctuation-only diffs must never
#    become memories at all.
# ---------------------------------------------------------------------------
formatting_only = [
    ("ask kabir to help", "Ask kabir to help.", "capitalization only"),
    ("dont forget the meeting", "Don't forget the meeting.", "punctuation only"),
    ("its going to rain", "It's going to rain.", "punctuation only"),
]
for asr, formatted, note in formatting_only:
    add("ordinary_formatting_no_memory", [{"asr": asr, "formatted": formatted}], asr, formatted, formatted, "IGNORE",
        f"Only {note} changed; no personal memory should be created from this observation.")

# ---------------------------------------------------------------------------
# 7) UNRELATED GRAMMAR REWRITE: large rewrites should not be misread as a
#    personal spelling preference.
# ---------------------------------------------------------------------------
grammar_rewrites = [
    ("ask him about it please", "Could you please ask him about it?"),
    ("send it now urgent", "Please send it immediately, this is urgent."),
]
for asr, formatted in grammar_rewrites:
    add("unrelated_grammar_no_memory", [{"asr": asr, "formatted": formatted}], asr, formatted, formatted, "IGNORE",
        "Large-scale grammar rewrites should not be captured as single-term memories.")

# ---------------------------------------------------------------------------
# 8) DEACTIVATED MEMORY: after deactivation the term must stop being applied,
#    exercised here via three observations then an explicit note that
#    deactivation is asserted by the runner (see runner.py DEACTIVATE step).
# ---------------------------------------------------------------------------
deactivate_pairs = [("tariq", "Tarique")]
for src, pref in deactivate_pairs:
    obs = [
        {"asr": f"ask {src} to review", "formatted": f"Ask {pref} to review."},
        {"asr": f"call {src} today", "formatted": f"Call {pref} today."},
    ]
    asr = f"email {src} now"
    formatted = f"Email {src.capitalize()} now."
    add("deactivated_memory_no_apply", obs, asr, formatted, formatted, "IGNORE",
        "This case is deactivated by the runner before processing to verify deactivation halts intervention.")

# ---------------------------------------------------------------------------
# 9) MULTI-WORD / COMPANY & PRODUCT terms.
# ---------------------------------------------------------------------------
multi_word = [
    ("open ai", "OpenAI", "partnership"),
    ("share point", "SharePoint", "migration"),
]
for src, pref, ctx in multi_word:
    obs = [
        {"asr": f"the {ctx} with {src} team", "formatted": f"The {ctx} with {pref} team."},
        {"asr": f"schedule a {ctx} with {src}", "formatted": f"Schedule a {ctx} with {pref}."},
    ]
    asr = f"follow up on the {src} {ctx}"
    formatted = f"Follow up on the {src.title()} {ctx}."
    expected = f"Follow up on the {pref} {ctx}."
    add("multi_word_term_apply", obs, asr, formatted, expected, "APPLY",
        f"Multi-word term '{src}' -> '{pref}' should transfer to a new sentence once ACTIVE.")

# ---------------------------------------------------------------------------
# 10) COMPETING PREFERRED FORMS: two different corrections offered for the
#     same source term -- Kivi should keep the first and treat the second as
#     conflicting evidence rather than silently switching.
# ---------------------------------------------------------------------------
competing = [("zara", "Zaraa", "Zarah")]
for src, pref_a, pref_b in competing:
    obs = [
        {"asr": f"ask {src} to send it", "formatted": f"Ask {pref_a} to send it."},
        {"asr": f"call {src} back", "formatted": f"Call {pref_a} back."},
        {"asr": f"remind {src} tonight", "formatted": f"Remind {pref_b} tonight."},  # competing correction
    ]
    asr = f"tell {src} the news"
    formatted = f"Tell {src.capitalize()} the news."
    add("competing_preferred_forms", obs, asr, formatted, formatted, "IGNORE",
        f"Original preferred form '{pref_a}' got a competing correction to '{pref_b}'; the resulting conflicting "
        "evidence drops confidence below the apply threshold, so Kivi abstains rather than picking a side.")

Path(OUT.parent).mkdir(parents=True, exist_ok=True)
with open(OUT, "w") as f:
    for c in cases:
        f.write(json.dumps(c) + "\n")

print(f"Wrote {len(cases)} cases to {OUT}")
categories = {}
for c in cases:
    categories[c["category"]] = categories.get(c["category"], 0) + 1
for cat, n in sorted(categories.items()):
    print(f"  {cat}: {n}")
