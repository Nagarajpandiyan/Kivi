-- Kivi word-level memory schema
-- Applied in order, tracked in schema_migrations. See backend/app/db.py:apply_migrations().

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id                          TEXT PRIMARY KEY,
    user_id                     TEXT NOT NULL REFERENCES users(id),
    source_term                 TEXT NOT NULL,      -- term as it appears in ASR
    preferred_term               TEXT NOT NULL,      -- term Kivi should produce instead
    normalized_source            TEXT NOT NULL,      -- lowercased, punctuation-stripped, for matching
    memory_type                 TEXT NOT NULL,       -- PERSON_NAME | PRODUCT_NAME | COMPANY_NAME | TECHNICAL_TERM | USER_SPECIFIC_TERM | SPELLING_VARIANT
    status                      TEXT NOT NULL,       -- CANDIDATE | ACTIVE | UPDATED | DEACTIVATED
    confidence                  REAL NOT NULL DEFAULT 0.0,
    supporting_evidence_count   INTEGER NOT NULL DEFAULT 0,
    conflicting_evidence_count  INTEGER NOT NULL DEFAULT 0,
    context_tokens              TEXT NOT NULL DEFAULT '[]',  -- JSON list of tokens seen near the term; used for relevance checks on common words
    is_common_word               INTEGER NOT NULL DEFAULT 0,  -- 1 if source term is an ordinary dictionary word (needs context to apply)
    created_at                  TEXT NOT NULL,
    updated_at                  TEXT NOT NULL,
    UNIQUE(user_id, normalized_source)
);

CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_normsrc ON memories(normalized_source);

CREATE TABLE IF NOT EXISTS memory_evidence (
    id              TEXT PRIMARY KEY,
    memory_id       TEXT NOT NULL REFERENCES memories(id),
    asr_text        TEXT NOT NULL,
    formatted_text  TEXT NOT NULL,
    evidence_type   TEXT NOT NULL,   -- SUPPORTING | CONFLICTING
    source_id       TEXT,            -- caller-supplied id for the observation, optional
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_memory ON memory_evidence(memory_id);

CREATE TABLE IF NOT EXISTS memory_relations (
    id                 TEXT PRIMARY KEY,
    memory_id          TEXT NOT NULL REFERENCES memories(id),
    related_memory_id  TEXT NOT NULL REFERENCES memories(id),
    relation_type      TEXT NOT NULL,  -- ALIAS | SAME_ENTITY | RELATED_TERM
    confidence         REAL NOT NULL DEFAULT 0.0,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_decisions (
    id           TEXT PRIMARY KEY,
    memory_id    TEXT,                 -- nullable: a decision can also represent "no memory matched"
    user_id      TEXT NOT NULL,
    input_asr    TEXT NOT NULL,
    input_formatted TEXT NOT NULL,
    decision     TEXT NOT NULL,        -- APPLY | IGNORE
    confidence   REAL,
    reason       TEXT NOT NULL,
    output_text  TEXT,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_user ON memory_decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_memory ON memory_decisions(memory_id);
