"""
A small, bundled list of ordinary English words.

Why this exists: a memory like "kiwi -> Kivi" is dangerous to auto-apply,
because "kiwi" is also an everyday word (the fruit, the bird, a nationality).
If the *source term* of a candidate memory is an ordinary dictionary word,
the decision engine requires supporting context (see
app/decision/engine.py) before it will APPLY the correction. Terms that are
NOT ordinary words (most personal names, product names, coined terms) do not
need this extra check.

This is intentionally a small, explainable, offline list rather than a
downloaded corpus or dictionary API -- it keeps the system reproducible with
no network access and keeps the reasoning inspectable. It is a deliberate
engineering trade-off, not a claim of linguistic completeness (documented as
a limitation in ARCHITECTURE.md / README.md).
"""

COMMON_WORDS = {
    "kiwi", "apple", "orange", "mango", "grape", "peach", "plum", "lemon", "lime",
    "current", "service", "review", "meeting", "call", "message", "email", "report",
    "team", "project", "task", "today", "tomorrow", "yesterday", "morning", "evening",
    "night", "week", "month", "year", "time", "day", "office", "home", "work",
    "friend", "family", "manager", "client", "customer", "order", "invoice",
    "ticket", "issue", "bug", "feature", "release", "build", "test", "code",
    "server", "client", "network", "system", "file", "folder", "document",
    "phone", "number", "address", "city", "country", "state", "street",
    "bank", "account", "card", "payment", "price", "cost", "budget", "sale",
    "book", "page", "chapter", "story", "movie", "show", "song", "music",
    "food", "coffee", "tea", "water", "lunch", "dinner", "breakfast", "snack",
    "car", "bike", "bus", "train", "flight", "trip", "travel", "hotel",
    "dog", "cat", "bird", "fish", "tree", "flower", "garden", "park",
    "school", "college", "class", "teacher", "student", "exam", "grade",
    "doctor", "hospital", "medicine", "health", "gym", "sport", "game", "match",
    "weather", "rain", "sun", "wind", "cloud", "snow", "storm",
    "red", "blue", "green", "yellow", "black", "white", "color",
    "big", "small", "fast", "slow", "new", "old", "good", "bad", "right", "left",
    "kivi",  # the product's own name is also a plausible ordinary-sounding word;
             # this is deliberate so "kivi" only auto-applies with supporting context
}


STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "and", "or", "but",
    "of", "in", "on", "at", "for", "with", "this", "that", "it", "its",
    "please", "could", "you", "i", "we", "he", "she", "they", "them",
    "ask", "call", "meet", "email", "tell", "remind", "check", "review",
    "follow", "up", "now", "today", "tomorrow", "tonight", "later", "soon",
    "back", "directly", "about", "regarding", "send", "join", "schedule",
    "him", "her", "me", "us", "immediately", "urgent",
}


def is_common_word(token: str) -> bool:
    return token.lower().strip(".,!?;:'\"") in COMMON_WORDS


def is_context_noise(token: str) -> bool:
    """True if `token` is too generic (a stopword or an ordinary dictionary
    word) to count as distinguishing context for an ambiguous common-word
    memory. Used by extraction.context_window() so that filler words like
    "check"/"the"/"service" don't trigger false-positive relevance matches
    in the decision engine (see decision/engine.py)."""
    t = token.lower().strip(".,!?;:'\"")
    return t in STOPWORDS or t in COMMON_WORDS
