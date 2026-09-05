# Kivi — Word-Level / Phonetic Memory

Kivi is a backend-focused full-stack system that learns user-specific word-level and phonetic preferences from ASR output and formatted text.

The system takes:

1. ASR output
2. Normally formatted text

and produces:

3. Memory-aware text using previously learned user-specific corrections.

### Example

**ASR**

```text
ask aditya to review the sarvam kiwi service
```

**Formatted**

```text
Ask Aditya to review the Sarvam Kiwi service.
```

**Memory-aware**

```text
Ask Aaditya to review the Sarvam Kivi service.
```

Kivi does not blindly replace words. It learns from repeated evidence, checks confidence and context, and can deliberately choose to **IGNORE** a correction when the evidence is insufficient or ambiguous.

---

# 1. What This Project Implements

Kivi implements a memory layer for ASR post-processing.

The system can:

- learn user-specific word preferences
- learn from normal ASR + formatted text pairs
- maintain supporting and conflicting evidence
- calculate confidence
- activate memories only after sufficient evidence
- retrieve memories relevant to the current user
- use context for ambiguous/common words
- apply corrections when confidence is high enough
- abstain when confidence is insufficient
- explain every APPLY/IGNORE decision
- expose memory and decision history through APIs
- provide a browser UI for teaching, testing, and inspection
- run locally with Python
- optionally run using Docker Compose
- run deterministic automated evaluation

---

# 2. Assignment Requirements

The implementation addresses the following requirements:

- Take ASR output and normally formatted text as input.
- Produce memory-aware output.
- Learn through ordinary use.
- Do not require a developer to manually insert memory records into the database.
- Treat abstention as a first-class behavior.
- Make decisions explainable.
- Make learned memories inspectable.
- Show evidence supporting a memory.
- Show conflicting evidence.
- Explain why a memory was applied or ignored.
- Work beyond the supplied example.
- Provide reproducible evaluation.

The assignment leaves technology choices open.

Kivi uses Python, FastAPI, SQLite, plain HTML/CSS/JavaScript, and deterministic logic.

---

# 3. Important: How to Run the Project After Downloading

This section is the most important part for a reviewer.

If you receive the project as:

```text
KIVI.zip
```

follow these steps.

## Step 1 — Download the ZIP

Download `KIVI.zip` to your computer.

## Step 2 — Extract the ZIP

Extract the ZIP file.

After extraction you should have a project folder similar to:

```text
KIVI/
├── backend/
├── frontend/
├── database/
├── data/
├── evaluation/
├── tests/
├── docker-compose.yml
├── .env.example
└── README.md
```

**Do not run the commands from inside `data/`.**

For Docker, run commands from the project root where `docker-compose.yml` is located.

For Python, run commands from `backend/`.

---

# 4. Recommended Way to Run Kivi

There are two supported ways to run the application:

### Option A — Python

This is the primary development/review path.

### Option B — Docker Compose

This is the convenient containerized path.

If Python is already installed, Option A is the simplest way to verify the project.

If Docker is installed and working, Option B can be used.

---

# 5. Option A — Run with Python

## Step 1 — Open a terminal

Navigate to the extracted Kivi project.

Example:

```bash
cd ~/Downloads/KIVI
```

Your exact path may be different.

Check that you are in the project root:

```bash
ls
```

You should see something similar to:

```text
backend
frontend
database
data
evaluation
tests
docker-compose.yml
README.md
```

---

# 6. Step 2 — Go to Backend

Run:

```bash
cd backend
```

---

# 7. Step 3 — Install Python Dependencies

Run:

```bash
pip install -r requirements.txt --break-system-packages
```

If your Python environment does not require `--break-system-packages`, you can use:

```bash
pip install -r requirements.txt
```

The project was developed with Python 3.12.3.

---

# 8. Step 4 — Database

You do **not** need to manually create `kivi.db`.

Kivi automatically creates/applies the database schema when the application starts.

The migration is located at:

```text
database/migrations/001_init.sql
```

The runtime database is:

```text
data/kivi.db
```

If `data/kivi.db` does not exist after extracting the ZIP, that is okay.

The application can create it.

---

# 9. Why `kivi.db` May Not Be Included in the ZIP

`kivi.db` is runtime/generated data.

It contains things such as:

- learned memories
- evidence
- decisions
- user data

The database schema is stored separately in:

```text
database/migrations/001_init.sql
```

This means a fresh copy of the repository can recreate the database.

The project therefore does not depend on a pre-existing SQLite database.

If a demo database is supplied separately, it can also be used.

---

# 10. Optional Manual Migration

If you want to manually apply the migrations before starting the server, from `backend/` run:

```bash
PYTHONPATH=. python3 -c "from app.db import apply_migrations; print(apply_migrations())"
```

This step is normally unnecessary because migrations are automatically applied during startup.

---

# 11. Step 5 — Start the Kivi Server

From:

```text
KIVI/backend
```

run:

```bash
KIVI_DB_PATH=../data/kivi.db PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application will be available at:

```text
http://localhost:8000/
```

---

# 12. Step 6 — Open Kivi in the Browser

Open:

```text
http://localhost:8000/
```

The Kivi UI provides:

- Teach It
- What It Remembers
- Try It
- Decision Trace
- Reset Everything

---

# 13. Health Check

You can verify that the backend is running by opening:

```text
http://localhost:8000/api/health
```

or running:

```bash
curl -s http://localhost:8000/api/health
```

---

# 14. Stop the Server

When finished, return to the terminal where Uvicorn is running and press:

```text
Ctrl+C
```

---

# 15. Optional Seed Data

Kivi includes optional seed data.

The seed file is:

```text
data/seed/seed.jsonl
```

It contains example learning observations such as:

```text
aditya → Aaditya
```

and:

```text
kiwi → Kivi
```

with relevant context.

---

# 16. Import Seed Data

If you want to populate the database with the example memories, first make sure the server is stopped.

From:

```text
KIVI/backend
```

run:

```bash
KIVI_DB_PATH=../data/kivi.db PYTHONPATH=. python3 -m app.import_data ../data/seed/seed.jsonl
```

Then start the server again:

```bash
KIVI_DB_PATH=../data/kivi.db PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/
```

---

# 17. Option B — Run with Docker

If Docker and Docker Compose are installed and working, you can run the entire application using Docker.

## Step 1 — Go to the Project Root

After extracting the ZIP:

```bash
cd KIVI
```

Make sure you are **not** inside:

```text
KIVI/data
```

and not inside:

```text
KIVI/backend
```

For Docker Compose, use the project root where:

```text
docker-compose.yml
```

is located.

---

# 18. Step 2 — Build and Start Kivi

Run:

```bash
docker compose up --build
```

Docker will:

1. build the application image
2. install dependencies
3. start the Kivi application
4. expose port `8000`

---

# 19. Step 3 — Open Kivi

Once Docker has started successfully, open:

```text
http://localhost:8000/
```

---

# 20. Docker in the Background

If you want Docker to run in the background:

```bash
docker compose up --build -d
```

Then open:

```text
http://localhost:8000/
```

---

# 21. Stop Docker

Run:

```bash
docker compose down
```

---

# 22. Full Docker Reset

To completely recreate the Docker environment and remove Docker volumes:

```bash
docker compose down -v
docker compose up --build
```

Be aware that:

```bash
docker compose down -v
```

removes the associated Docker volume data.

---

# 23. Docker Evaluation

The evaluation service can be run using:

```bash
docker compose run --rm evaluation
```

---

# 24. Project Structure

The extracted project should look approximately like:

```text
KIVI/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   │
│   │   ├── memory/
│   │   │   ├── lifecycle.py
│   │   │   ├── extraction.py
│   │   │   ├── validation.py
│   │   │   └── confidence.py
│   │   │
│   │   ├── retrieval/
│   │   │   └── retrieve.py
│   │   │
│   │   ├── decision/
│   │   │   └── engine.py
│   │   │
│   │   ├── formatter/
│   │   │   └── format.py
│   │   │
│   │   ├── db.py
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── database/
│   └── migrations/
│       └── 001_init.sql
│
├── data/
│   ├── seed/
│   │   └── seed.jsonl
│   └── kivi.db
│
├── evaluation/
│   ├── generate_dataset.py
│   ├── runner.py
│   └── results/
│       ├── results.json
│       ├── metrics.json
│       └── report.md
│
├── tests/
│
├── docker-compose.yml
├── .env.example
└── README.md
```

`kivi.db` is runtime state and does not have to be committed to source control.

---

# 25. Architecture

```text
                         Browser
                            │
                            │ HTTP
                            ▼
                 ┌──────────────────────┐
                 │      FastAPI         │
                 │     backend/app      │
                 └──────────┬───────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       Learning        Retrieval       Decision
       Pipeline         Engine          Engine
             │              │              │
             ▼              │              ▼
       Extraction           │          APPLY / IGNORE
       Validation            │              │
       Confidence            │              ▼
       Lifecycle             │         Formatter
             │               │              │
             └───────────────┴──────────────┘
                            │
                            ▼
                       SQLite DB
                       data/kivi.db
```

---

# 26. Learning Pipeline

Kivi learns from ordinary usage.

The learning flow is:

```text
ASR + Formatted Text
        │
        ▼
Candidate Extraction
        │
        ▼
Candidate Validation
        │
        ▼
Existing Memory Lookup
        │
        ├───────────────┐
        │               │
        ▼               ▼
   New Memory       Existing Memory
        │               │
        ▼               ├── agrees → support +1
    CANDIDATE           │
                        └── disagrees → conflict +1
                                │
                                ▼
                         Confidence Update
                                │
                                ▼
                         Lifecycle Update
```

---

# 27. Candidate Extraction

Kivi compares ASR text with the formatted text.

The comparison uses:

```python
difflib.SequenceMatcher
```

The system:

- tokenizes the text
- normalizes words
- separates punctuation
- aligns the two versions
- identifies replacement candidates

Pure insertions/deletions are not automatically treated as memory corrections.

---

# 28. Candidate Validation

Kivi rejects changes that look like ordinary formatting rather than user-specific memory.

Examples that are rejected:

```text
aditya → Aditya
```

because it is only capitalization.

Punctuation-only changes are also rejected.

Candidates with excessive edit distance are rejected.

Candidates shorter than two characters are rejected.

Multi-word changes such as:

```text
open ai → OpenAI
```

can be accepted.

---

# 29. Memory Lifecycle

A memory moves through lifecycle states:

```text
CANDIDATE
    │
    │ enough supporting evidence
    ▼
ACTIVE
    │
    │ changed evidence
    ▼
UPDATED
    │
    │ confidence becomes too low
    ▼
DEACTIVATED
```

Configured thresholds:

```text
MIN_SUPPORTING_FOR_ACTIVE = 2

CONFIDENCE_ACTIVE_THRESHOLD = 0.60

CONFIDENCE_APPLY_THRESHOLD = 0.60

CONFIDENCE_DEACTIVATE_THRESHOLD = 0.35
```

---

# 30. Confidence Calculation

Kivi calculates:

```text
confidence =
supporting /
(supporting + conflicting + 1)
```

For example:

```text
supporting = 2
conflicting = 0
```

produces:

```text
2 / (2 + 0 + 1)
= 0.67
```

This is above the `0.60` activation/application threshold.

---

# 31. Conflicting Evidence

Kivi does not immediately overwrite a learned preference when a conflicting observation appears.

Example:

```text
aditya → Aaditya
```

supporting evidence.

Then:

```text
aditya → Aditya
```

conflicting evidence.

Then another:

```text
aditya → Aaditya
```

supporting evidence.

Final counts:

```text
supporting = 2
conflicting = 1
```

Confidence:

```text
2 / (2 + 1 + 1)
= 0.50
```

Therefore the system ignores the memory because confidence is below `0.60`.

This is intentionally conservative.

---

# 32. Common-Word Ambiguity

Kivi handles ambiguous common words differently.

Example:

```text
kiwi → Kivi
```

The word `kiwi` can refer to the fruit or to a user-specific product/company term.

Therefore context matters.

For example:

```text
Ask Aditya to review the Sarvam Kiwi service.
```

contains relevant context:

```text
Sarvam
```

and can justify:

```text
Kivi
```

But:

```text
I ate a kiwi yesterday.
```

should remain:

```text
I ate a kiwi yesterday.
```

The system should not blindly apply:

```text
kiwi → Kivi
```

to every occurrence.

---

# 33. Retrieval

Kivi retrieves memories belonging to the current user.

A memory is eligible for consideration when its normalized source term appears in the normalized input.

Deactivated memories are not retrieved for application.

---

# 34. Decision Engine

For each candidate memory, Kivi checks:

### 1. Memory Status

The memory must be:

```text
ACTIVE
```

or:

```text
UPDATED
```

### 2. Confidence

The memory must satisfy:

```text
confidence >= 0.60
```

### 3. Evidence Balance

Conflicting evidence must not be greater than supporting evidence.

### 4. Context

Common-word memories need meaningful contextual support.

If the checks pass:

```text
APPLY
```

Otherwise:

```text
IGNORE
```

---

# 35. Explainability

Every decision has a reason.

For example:

```text
Decision: APPLY

Reason:
Memory is active, confidence is above threshold,
and the input contains relevant context.
```

Or:

```text
Decision: IGNORE

Reason:
Memory confidence is below the application threshold.
```

Or:

```text
Decision: IGNORE

Reason:
Common-word memory lacks relevant contextual evidence.
```

This allows a reviewer to inspect why the system acted.

---

# 36. Provenance

Kivi stores evidence in:

```text
memory_evidence
```

and decision history in:

```text
memory_decisions
```

Evidence includes:

- ASR input
- formatted input
- evidence type
- source ID
- timestamp

Decision records include:

- input
- decision
- confidence
- reason
- timestamp

---

# 37. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/memory/learn` | Learn a new observation |
| GET | `/api/memory` | List memories |
| GET | `/api/memory/{id}` | Inspect memory |
| POST | `/api/memory/{id}/deactivate` | Deactivate memory |
| POST | `/api/transcript/process` | Process ASR + formatted text |
| GET | `/api/decisions/{id}` | Inspect decision |
| POST | `/api/import` | Import observations |
| POST | `/api/reset` | Reset runtime data |

---

# 38. Example: Teach Kivi

You can teach Kivi through the API.

```bash
curl -s -X POST localhost:8000/api/memory/learn \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"user_1",
    "asr":"ask aditya to call me",
    "formatted":"Ask Aaditya to call me."
  }'
```

One observation creates a candidate.

A second consistent observation can provide enough evidence for activation.

---

# 39. Example: List Memories

```bash
curl -s "http://localhost:8000/api/memory?user_id=user_1"
```

---

# 40. Example: Process a Transcript

After the memory has enough evidence:

```bash
curl -s -X POST localhost:8000/api/transcript/process \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"user_1",
    "asr":"ask aditya about the meeting",
    "formatted":"Ask Aditya about the meeting."
  }'
```

Expected output:

```text
Ask Aaditya about the meeting.
```

The response also contains decision information.

---

# 41. Example: Inspect a Memory

After obtaining a memory ID:

```bash
curl -s "http://localhost:8000/api/memory/<memory_id>"
```

This can show:

- memory
- confidence
- supporting evidence
- conflicting evidence
- decision history

---

# 42. Example: Inspect a Decision

After obtaining a decision ID:

```bash
curl -s "http://localhost:8000/api/decisions/<decision_id>"
```

This shows why Kivi decided to APPLY or IGNORE.

---

# 43. Example: Deactivate a Memory

```bash
curl -s -X POST \
  "http://localhost:8000/api/memory/<memory_id>/deactivate"
```

The memory becomes:

```text
DEACTIVATED
```

and is not used for future automatic application.

---

# 44. Reset the Application

To reset runtime data:

```bash
curl -s -X POST localhost:8000/api/reset
```

This resets the runtime state while retaining the database schema.

---

# 45. UI Walkthrough

Open:

```text
http://localhost:8000/
```

## Teach It

Enter:

```text
ASR:
ask aditya to call me

Formatted:
Ask Aaditya to call me.
```

Submit the example.

Repeat with another consistent observation.

## What It Remembers

Inspect the learned memory.

You should be able to see information such as:

```text
aditya → Aaditya
```

along with:

- status
- confidence
- supporting evidence
- conflicting evidence

## Try It

Enter:

```text
ASR:
ask aditya about the meeting

Formatted:
Ask Aditya about the meeting.
```

Kivi should produce:

```text
Ask Aaditya about the meeting.
```

when the memory is active and applicable.

## Decision Trace

Inspect:

```text
APPLY
```

or:

```text
IGNORE
```

and the explanation for that decision.

---

# 46. Test Abstention

Use the common-word memory:

```text
kiwi → Kivi
```

Then test:

```text
I ate a kiwi yesterday.
```

Kivi should preserve:

```text
I ate a kiwi yesterday.
```

rather than blindly producing:

```text
I ate a Kivi yesterday.
```

The decision trace should explain why the memory was ignored.

---

# 47. Evaluation

The project includes a deterministic evaluation suite.

Current evaluation:

```text
30 cases
10 categories
```

Each case uses an isolated user ID so that one evaluation case does not accidentally teach another case.

---

# 48. Run Evaluation

From the project root:

```bash
PYTHONPATH=backend python3 -m evaluation.runner
```

Results are written to:

```text
evaluation/results/results.json
evaluation/results/metrics.json
evaluation/results/report.md
```

---

# 49. Evaluation Dataset

The dataset generator is:

```text
evaluation/generate_dataset.py
```

To regenerate the dataset:

```bash
python3 evaluation/generate_dataset.py
```

---

# 50. Automated Tests

The project includes:

```text
22 automated tests
```

Run:

```bash
PYTHONPATH=backend python3 -m pytest tests/ -v
```

---

# 51. Current Evaluation Result

The current documented result is:

```text
30/30 passing
```

This should be interpreted honestly.

The evaluation dataset was developed together with the implementation.

Therefore:

```text
30/30
```

demonstrates consistency with the project's evaluation suite.

It does not prove:

- 100% real-world accuracy
- universal ASR correction accuracy
- large-scale production robustness
- broad linguistic coverage
- generalization to arbitrary unseen data

---

# 52. AI / LLM Usage

Kivi does not use an LLM.

Model calls:

```text
0
```

Estimated model/API cost:

```text
$0
```

The pipeline is deterministic.

This means:

- no API key required
- no model dependency
- no token cost
- no network dependency
- reproducible results
- deterministic decisions

---

# 53. Database

Kivi uses:

```text
SQLite
```

through:

```text
sqlite3
```

There is no ORM.

The schema is defined in:

```text
database/migrations/001_init.sql
```

The runtime database is:

```text
data/kivi.db
```

---

# 54. Environment Variables

An optional environment file is provided:

```text
.env.example
```

The main configuration variable is:

```text
KIVI_DB_PATH
```

Default:

```text
data/kivi.db
```

No API keys are required.

---

# 55. Python Version

The implementation was developed and tested using:

```text
Python 3.12.3
```

The project does not require Node.js or npm.

---

# 56. Limitations

### 1. Common-word list

Common-word ambiguity uses a hand-built list.

It is deterministic but not linguistically complete.

### 2. One memory per normalized source term

The current design stores one memory per:

```text
(user, normalized source term)
```

Competing preferences therefore become conflicting evidence rather than separate memories.

### 3. Deactivation

Deactivated memories do not automatically reactivate.

### 4. Evaluation size

The evaluation contains 30 cases.

It is useful for reproducibility but is not a large independent benchmark.

### 5. English

The current tokenizer and ambiguity rules are designed for English.

---

# 57. Git / Repository Recommendations

The following generated/runtime files should normally not be committed:

```gitignore
data/kivi.db
.env
__pycache__/
.pytest_cache/
*.pyc
```

The following should be committed:

```text
database/migrations/
data/seed/
evaluation/
tests/
backend/
frontend/
docker-compose.yml
README.md
```

---

# 58. What a Reviewer Should Do

If reviewing from the ZIP, the simplest workflow is:

### 1. Download

```text
KIVI.zip
```

### 2. Extract

Extract to:

```text
KIVI/
```

### 3. Open terminal

Go to the extracted project:

```bash
cd KIVI
```

### 4. Start with Docker

If Docker is available:

```bash
docker compose up --build
```

### 5. Open browser

Go to:

```text
http://localhost:8000/
```

### 6. Test the UI

Use:

```text
Teach It
```

then:

```text
What It Remembers
```

then:

```text
Try It
```

then:

```text
Decision Trace
```

### 7. Run tests

In another terminal:

```bash
PYTHONPATH=backend python3 -m pytest tests/ -v
```

### 8. Run evaluation

```bash
PYTHONPATH=backend python3 -m evaluation.runner
```

---

# 59. If Docker Is Not Available

Use Python instead.

From the extracted project:

```bash
cd KIVI/backend
```

Install:

```bash
pip install -r requirements.txt --break-system-packages
```

Start:

```bash
KIVI_DB_PATH=../data/kivi.db PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/
```

---

# 60. One-Command Docker Startup

For a reviewer who simply wants to run the application:

```bash
cd KIVI
docker compose up --build
```

Then open:

```text
http://localhost:8000/
```

That is the intended simplest Docker workflow.

---

# 61. One-Command Python Startup After Dependencies

Once dependencies are installed:

```bash
cd KIVI/backend
KIVI_DB_PATH=../data/kivi.db PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open:

```text
http://localhost:8000/
```

---

# 62. Complete Verification

A reviewer can verify the complete project using:

```bash
# From project root

PYTHONPATH=backend python3 -m pytest tests/ -v

PYTHONPATH=backend python3 -m evaluation.runner
```

Then start the server:

```bash
cd backend

KIVI_DB_PATH=../data/kivi.db \
PYTHONPATH=. \
uvicorn app.main:app \
--host 0.0.0.0 \
--port 8000
```

Open:

```text
http://localhost:8000/
```

---

# 63. Final Submission Information

Before submitting the assignment, fill in:

```text
GitHub Repository:
<YOUR_GITHUB_REPOSITORY_URL>

Final Commit SHA:
<YOUR_FINAL_COMMIT_SHA>

Hosted URL:
<YOUR_HOSTED_URL_OR_N/A>
```

Do not put placeholder values in the final submission.
