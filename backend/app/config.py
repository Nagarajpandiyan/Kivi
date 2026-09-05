import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Where the SQLite file lives. Overridable so the evaluation runner can point
# at an isolated database instead of the interactive demo's database.
DB_PATH = os.environ.get("KIVI_DB_PATH", str(PROJECT_ROOT / "data" / "kivi.db"))

MIGRATIONS_DIR = PROJECT_ROOT / "database" / "migrations"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SEED_FILE = PROJECT_ROOT / "data" / "seed" / "seed.jsonl"

# --- Learning / confidence thresholds -------------------------------------
# These are OUR engineering choices, not Sarvam requirements. They are
# documented and justified in ARCHITECTURE.md and validated by the
# evaluation harness in evaluation/.

MIN_SUPPORTING_FOR_ACTIVE = 2        # a memory needs >=2 supporting observations
CONFIDENCE_ACTIVE_THRESHOLD = 0.60   # and confidence >= this, to leave CANDIDATE
CONFIDENCE_DEACTIVATE_THRESHOLD = 0.35  # ACTIVE memory drops below this -> DEACTIVATED
CONFIDENCE_APPLY_THRESHOLD = 0.60    # decision engine will not APPLY below this
LAPLACE_SMOOTHING_K = 1.0            # confidence = supporting / (supporting + conflicting + K)

# A candidate whose source/preferred terms differ only by case or
# punctuation is ordinary formatting, not a personal memory.
MIN_TERM_LENGTH = 2
MAX_RELATIVE_EDIT_DISTANCE = 0.6     # candidates that differ "too much" are rejected
