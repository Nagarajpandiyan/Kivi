"""
Retrieval.

For a new (asr, formatted) processing request, find the ACTIVE/UPDATED (and,
for transparency, CANDIDATE) memories belonging to this user whose source
term actually appears in the request. We do not scan every memory the user
has ever had -- only ones textually present in this input are retrieved,
which keeps retrieval relevant, fast (indexed lookup per token), and easy to
explain ("this memory matched because the word 'aditya' appears in the
input").
"""

import sqlite3

from app.db import row_to_memory
from app.memory.extraction import normalize_token, tokenize


def retrieve_relevant_memories(conn: sqlite3.Connection, user_id: str, asr: str, formatted: str) -> list[dict]:
    input_tokens = [normalize_token(t) for t in tokenize(asr) + tokenize(formatted)]
    input_tokens = [t for t in input_tokens if t]
    if not input_tokens:
        return []
    input_phrase = " " + " ".join(input_tokens) + " "

    # Scanning per-user memories (rather than a single-token index lookup)
    # lets multi-word terms like "open ai" -> "OpenAI" match as a phrase,
    # not just single tokens. This is still bounded and fast: it only scans
    # the memories belonging to the current user, not the whole table.
    rows = conn.execute(
        "SELECT * FROM memories WHERE user_id = ? AND status != 'DEACTIVATED'",
        (user_id,),
    ).fetchall()

    matched = []
    for row in rows:
        mem = row_to_memory(row)
        needle = " " + mem["normalized_source"] + " "
        if needle in input_phrase:
            matched.append(mem)
    return matched
