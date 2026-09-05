# Architecture

## 1. System overview

```
                 ┌─────────────────────────────────────────────┐
                 │                  frontend/                   │
                 │        (static HTML/CSS/JS, no build)         │
                 └───────────────────┬───────────────────────────┘
                                     │ fetch() -> /api/*
┌────────────────────────────────────▼──────────────────────────────────┐
│                         backend/app  (FastAPI)                         │
│                                                                          │
│  api/routes.py  ── HTTP layer, request/response only                    │
│      │                                                                   │
│      ├─ memory/lifecycle.py  ── learning orchestration (the "brain")    │
│      │     ├─ memory/extraction.py   candidate detection (diff)         │
│      │     ├─ memory/validation.py   candidate validation               │
│      │     └─ memory/confidence.py   confidence scoring                 │
│      │                                                                   │
│      ├─ retrieval/retrieve.py  ── find memories relevant to a request   │
│      ├─ decision/engine.py     ── APPLY / IGNORE + reason per memory    │
│      └─ formatter/format.py    ── actually rewrite the output text      │
│                                                                          │
│  db.py  ── sqlite3 connection + migration runner                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                          database/migrations/001_init.sql
                                    │
                              data/kivi.db  (SQLite)
```

No component calls an LLM. See section 10.

## 2. Data flow

### Learning (`POST /memory/learn`, also used by `/import` and the UI's "Teach it")

```
(asr, formatted)
   -> extraction.extract_candidates()      word-level diff -> RawCandidate list
   -> validation.validate_candidate()      ordinary formatting? too different? -> keep or reject
   -> lifecycle.learn():
        - look up existing memory for this (user, normalized source term)
        - none yet      -> create memory, status=CANDIDATE, 1 supporting evidence
        - exists, agrees -> +1 supporting evidence, recompute confidence
        - exists, disagrees -> +1 conflicting evidence, recompute confidence
        - also: if an existing memory's term appears in the ASR but the
          formatted text left it *uncorrected*, that is itself conflicting
          evidence (the "expected" correction didn't happen)
   -> confidence.compute_confidence()
   -> lifecycle transition (CANDIDATE -> ACTIVE -> UPDATED -> DEACTIVATED)
```

### Processing (`POST /transcript/process`)

```
(asr, formatted)
   -> retrieval.retrieve_relevant_memories()   memories whose term appears in this input
   -> decision.decide_all()                     APPLY / IGNORE + reason, per memory
   -> formatter.apply_memory()                  rewrite formatted text for APPLY decisions
   -> persist a memory_decisions row per memory considered (provenance)
   -> return {output, decision, intervened, memories_used, decisions[], reason}
```

## 3. Memory abstraction

```json
{
  "id": "mem_...",
  "user_id": "user_1",
  "source_term": "Aditya",
  "preferred_term": "Aaditya",
  "normalized_source": "aditya",
  "memory_type": "PERSON_NAME",
  "status": "ACTIVE",
  "confidence": 0.94,
  "supporting_evidence_count": 5,
  "conflicting_evidence_count": 0,
  "context_tokens": ["sarvam", "review"],
  "is_common_word": false
}
```

**What Kivi can distinguish, and why it matters:**

- **Ordinary formatting vs. a real memory candidate** (`validation.py`).
  Capitalizing "aditya" -> "Aditya" is something any formatter should do
  for anyone; it must never become a per-user memory, or Kivi would "learn"
  thousands of meaningless facts and its memory list would be useless.
- **Case/punctuation-only vs. letter-level spelling difference.** Only the
  latter is a candidate. This is the line between "the formatter did its
  job" and "the user has a specific spelling preference."
- **A memory whose source term is an ordinary dictionary word** (`kiwi`,
  `current`, `orange`, ...) vs. one that isn't (`aditya`). This matters
  because ordinary words are ambiguous -- "kiwi" the fruit and "Kivi" the
  product sound identical -- so applying the correction requires
  supporting context (see section 6). Non-ordinary terms don't need this
  extra gate; there's no common English word "aditya" competing for the
  same sound.
- **Supporting vs. conflicting evidence**, tracked as separate counters
  rather than a single running "confidence" number, so provenance survives
  even after confidence changes (see section 7).

**What it deliberately does not distinguish:** the taxonomy of
`memory_type` (PERSON_NAME / PRODUCT_NAME / COMPANY_NAME / TECHNICAL_TERM /
USER_SPECIFIC_TERM / SPELLING_VARIANT) is a labeling convenience for the
UI, produced by a small heuristic (a short list of common first-name
patterns, otherwise "does it look like a proper noun") -- it does **not**
gate any decision. Getting the label wrong (e.g. classifying a company name
as USER_SPECIFIC_TERM) has no effect on whether the memory is applied. Only
`is_common_word`, `status`, and `confidence` are decision-relevant.

## 4. Candidate extraction (`memory/extraction.py`)

ASR and formatted text are tokenized (words and punctuation as separate
tokens), normalized (lowercased, edge punctuation stripped), and aligned
with `difflib.SequenceMatcher`. Each `replace` opcode of up to 3 tokens on
either side becomes a `RawCandidate`. Leading/trailing tokens with no
letters (pure punctuation swept in by the alignment) are trimmed off the
edges of the candidate before it's considered, so a trailing "." never
contaminates a term like "OpenAI".

`equal` and `insert`/`delete` opcodes are not candidates at all -- an
insertion (e.g. the formatter adding "Could you please") is grammar, not a
personal term.

## 5. Candidate validation (`memory/validation.py`)

Rejected as ordinary formatting:
- source and preferred terms are identical once lowercased (pure case
  change), OR (for single-word terms) identical once all punctuation is
  stripped (pure punctuation change, e.g. "dont" vs "don't").
- the terms differ by more than 60% of their length in edit distance --
  that's a grammar rewrite or an unrelated ASR error, not a spelling
  preference (`MAX_RELATIVE_EDIT_DISTANCE` in `config.py`).
- either term is shorter than 2 characters.

Multi-word terms (e.g. "open ai" -> "OpenAI") are exempt from the "pure
case" identity check on their *joined* form, because merging two words into
one **is** the personal preference being taught, even when no individual
letter's case changed.

Accepted candidates are tagged with a `memory_type` guess and an
`is_common_word` flag (see section 6).

## 6. Confidence (`memory/confidence.py`)

```
confidence = supporting / (supporting + conflicting + 1)
```

Add-one (Laplace) smoothing. Properties, all deliberate:
- One supporting observation alone gives confidence 0.5 -- never enough by
  itself to leave CANDIDATE status (see section 7's `MIN_SUPPORTING_FOR_ACTIVE
  = 2`). A single correction could be a one-off, not a standing preference.
- Confidence rises smoothly with consistent evidence (2 -> 0.67, 5 -> 0.83, ...)
  and never reaches 1.0.
- A single piece of conflicting evidence hurts more, proportionally, when
  supporting evidence is still low -- exactly when we should be least sure.

Thresholds (`config.py`, all validated against `evaluation/`):
- `MIN_SUPPORTING_FOR_ACTIVE = 2`
- `CONFIDENCE_ACTIVE_THRESHOLD = 0.60`
- `CONFIDENCE_APPLY_THRESHOLD = 0.60`
- `CONFIDENCE_DEACTIVATE_THRESHOLD = 0.35`

## 7. Memory lifecycle (`memory/lifecycle.py`)

```
   1st supporting evidence
CANDIDATE ──────────────────────────► CANDIDATE (still, until threshold met)
   │  2nd+ supporting evidence AND confidence >= 0.60
   ▼
ACTIVE ───────────────────────────────► UPDATED  (confidence changed, still >= 0.35)
   │
   │  confidence drops below 0.35 (conflicting evidence)
   ▼
DEACTIVATED  ◄── or explicit POST /memory/{id}/deactivate
```

We never overwrite `preferred_term` on conflicting evidence -- see the
worked example in section 9. A `DEACTIVATED` memory does not silently
reactivate from new matching evidence; it stays inert (the observation is
still logged for provenance) until someone deliberately re-teaches it,
which will create a **new** memory only if the old row is deleted -- in the
current schema a deactivated row's `(user_id, normalized_source)` still
occupies the uniqueness constraint, so in practice deactivation here is
treated as durable. This is a documented limitation (section 12), not an
oversight: "should a deactivated memory be able to reactivate on its own"
is exactly the kind of aggressive-correction behavior section 25 asks us
to avoid defaulting to.

## 8. Retrieval (`retrieval/retrieve.py`)

For a processing request, all of the user's non-deactivated memories are
scanned (bounded by that user's memory count, not the whole table) and a
memory is retrieved if its `normalized_source` phrase appears as a
substring of the space-joined, normalized tokens of `asr + formatted`. This
handles both single-word ("aditya") and multi-word ("open ai") terms with
one code path.

## 9. Decision engine (`decision/engine.py`)

For each retrieved memory, checked in order (first failing check is the
stated reason):

1. `status` must be `ACTIVE`/`UPDATED` -- a `CANDIDATE` hasn't earned
   enough evidence yet.
2. `confidence >= CONFIDENCE_APPLY_THRESHOLD` (0.60).
3. `conflicting_evidence_count < supporting_evidence_count` -- an explicit,
   separately-explainable belt-and-braces check on top of confidence.
4. If `is_common_word`, the current input must share at least one token
   with the memory's stored `context_tokens` (see section 4's extraction
   and the note below on context filtering), or the decision is IGNORE.

Anything that clears all four is APPLY.

**Worked example -- conflicting evidence (why we don't overwrite):**
Observation 1: `aditya -> Aaditya` (supporting). Observation 2:
`aditya -> Aditya` (no correction applied -- conflicting). Observation 3:
`aditya -> Aaditya` (supporting again). Result: supporting=2,
conflicting=1, confidence = 2/(2+1+1) = 0.5, which is **below** the 0.60
apply threshold -- Kivi abstains on the next mention of "aditya" rather
than guessing which spelling is currently intended. `preferred_term`
stays `Aaditya` throughout; it is never flipped back to `Aditya` on the
conflicting observation.

**Context filtering:** naive "neighboring word" context would include
filler words ("the", "check", "service") that appear in almost every
sentence, making the relevance gate meaningless. `context_tokens` therefore
excludes both a small stopword list and words already in the
common-word list (`common_words.py`, `is_context_noise`) -- only
distinguishing terms like "sarvam" or "billing" count as context.

## 10. AI/LLM usage

**None.** Every decision in this pipeline -- extraction, validation,
confidence, lifecycle, retrieval, and the APPLY/IGNORE decision -- is
deterministic Python, matching the brief's preference for deterministic
backend logic wherever possible (section 47 of the original instruction
doc, and implicit throughout the PDF's emphasis on explainability). No API
key is required to run this project; `evaluation/metrics.json` reports
`model_calls: 0` and `estimated_cost_usd: 0.0` for every run, truthfully,
because none are made.

This is a stated trade-off, not a claim that ambiguity resolution or
candidate classification couldn't benefit from a language model -- see
Limitations below.

## 11. Provenance

Every memory's evidence is stored in `memory_evidence` (asr_text,
formatted_text, evidence_type, source_id, timestamp) and every decision is
stored in `memory_decisions` (input, decision, confidence, reason,
timestamp). `GET /memory/{id}` returns the memory plus its full evidence
and decision history; `GET /decisions/{id}` returns one decision record.
Nothing about "why does Kivi believe this" is hidden behind a log file the
reviewer can't reach through the API/UI.

## 12. Known limitations

- **Ambiguity detection is a hand-built word list, not a language model or
  dictionary API.** It's small, offline, and reproducible, but not
  linguistically complete -- an ordinary word missing from
  `common_words.py` would be treated as unambiguous and could over-apply.
- **One memory row per (user, normalized source term).** Two genuinely
  different people who both sound like "aditya" cannot be modeled as two
  separate memories; competing corrections instead show up as conflicting
  evidence on a single row, which erodes confidence rather than
  disambiguating between them. Modeling multiple senses of one term would
  need per-context memory rows, which we judged unnecessary complexity for
  this system's scope (see brief section 19: don't build relationships
  unless they provide real value).
- **Deactivation is durable within a session**, as discussed in section 7 --
  there's no automatic path back to CANDIDATE for a deactivated term.
- **The 30-case evaluation dataset is small and self-consistent** (we wrote
  both the cases and the system, so 100% pass is a check that the
  documented rules are implemented correctly and consistently -- not
  independent evidence of generalization to unseen, adversarial, or
  larger-scale transcripts). See `evaluation/results/report.md` for exactly
  which cases exist.
- **English-only.** Tokenization, the common-word list, and the name-hint
  list assume English text.
