"""
Documented data-import mechanism (see RUN.md).

Usage:
    python -m app.import_data ../data/seed/seed.jsonl

Reads a .jsonl file of {"user_id", "asr", "formatted", "source_id"?}
observations and replays each one through app.memory.lifecycle.learn(),
exactly like calling POST /memory/learn -- there is no separate "insert a
memory directly" path, so imported data goes through the same candidate
extraction / validation / evidence / confidence pipeline as live traffic.
"""

import json
import sys

from app.db import apply_migrations, get_conn
from app.memory.lifecycle import learn


def main(path: str):
    apply_migrations()
    created, updated, observations = 0, 0, 0
    with open(path) as f, get_conn() as conn:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            result = learn(
                conn,
                item.get("user_id", "user_1"),
                item["asr"],
                item["formatted"],
                item.get("source_id"),
            )
            observations += 1
            created += len(result.memories_created)
            updated += len(result.memories_updated)
    print(f"Imported {observations} observations -> {created} memories created, {updated} memories updated.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.import_data <path-to-jsonl>")
        sys.exit(1)
    main(sys.argv[1])
