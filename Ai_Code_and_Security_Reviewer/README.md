# AI Code & PR Reviewer

An AI-powered code review tool that analyzes GitHub pull requests and posts inline review comments directly on the PR. Built with FastAPI, Gemini, and the GitHub Review API, and deployed on AWS EC2.

---

## What It Does

Given a GitHub repository and optionally a PR's base/head refs, the tool:

1. **Clones** the repository and checks out the PR head.
2. **Parses the diff** to find changed files and the exact line numbers added or modified in the PR.
3. **Builds review context** — for Python files, the changed code plus the definitions of the functions/classes those files import from elsewhere in the repo.
4. **Sends the focused context to Gemini** with a structured prompt that enforces line-number grounding and security heuristics.
5. **Filters findings** to only lines that were actually added or modified in the PR.
6. **Posts a single GitHub Review** with inline comments on the PR, and persists the review and findings to a database.

Review status and findings are queryable through the API.

> **Supported languages:** Python. The file scanner also picks up `.js`, `.ts`, `.jsx`, and `.tsx` files, but chunking and import analysis use Python's `ast` module, so non-Python files contribute no reviewable code. Point the tool at Python repositories for meaningful results.

---

## Architecture

```
POST /reviews/
      │
      ▼
Review row created (status=pending)
      │
      ▼  (background task)
Clone repo ──► git diff ──► parse_diff ──► changed files + added lines
      │
      ▼
Build file contexts (changed + upstream dependencies)
      │
      ▼
Rank & filter chunks (symbol-level for upstream, dependency + security weighting)
      │
      ▼
LLM (Gemini) ──► ReviewFindings (JSON)
      │
      ▼
Filter findings to PR added lines
      │
      ├──► Persist findings (SQLAlchemy)
      └──► POST GitHub Review with inline comments
      │
      ▼
Review status = completed / failed
```

---

## Project Structure

```
Ai_Code_and_Security_Reviewer/
├── app/
│   ├── api/
│   │   ├── dependancies.py       # FastAPI dependency wiring
│   │   └── reviews.py            # /reviews endpoints
│   ├── core/
│   │   └── config.py             # configuration
│   ├── models/
│   │   ├── db_review.py          # Review table
│   │   └── db_finding.py         # Finding table
│   ├── schemas/
│   │   ├── file.py               # file-related schemas
│   │   ├── finding.py            # FindingCreate, ReviewFindings
│   │   └── review.py             # ReviewCreate
│   ├── repositories/
│   │   └── review_repository.py  # DB access
│   ├── services/
│   │   ├── ai_service.py         # prompt building + Gemini call
│   │   ├── ast_service.py        # AST chunking + import extraction
│   │   ├── context_service.py    # chunk ranking, token budgeting, symbol filtering
│   │   ├── dependancy_service.py # module index, dependency scores, import resolution
│   │   ├── diff_parser.py        # parses git diff into ChangedFile objects
│   │   ├── file_service.py       # file discovery, reading, context building
│   │   ├── git_service.py        # clone, diff, ref handling
│   │   ├── github_service.py     # posts inline review comments
│   │   └── review_service.py     # orchestrates the full pipeline
│   ├── db.py                     # engine + session
│   ├── init_db.py                # creates tables on startup
│   └── main.py                   # FastAPI app
├── data/                         # SQLite volume mount (runtime)
├── fixtures/sample_repo/         # local fixtures for tests
├── scripts/                      # helper scripts
├── tests/                        # pytest suite
├── docker-compose.yaml
├── Dockerfile
├── entrypoint.sh                 # runs init_db, then Gunicorn
├── pytest.ini
├── README.md
└── requirements.txt
```

---

## Key Design Decisions

**Focused context, not the whole repo.**
Sending an entire codebase to an LLM is slow, expensive, and noisy. This tool sends only the changed code plus the specific functions/classes those files import. Upstream context is resolved via AST import analysis and symbol-level filtering, so a large dependency file contributes only the pieces actually used.

**Grounding the model on real line numbers.**
Every chunk in the prompt is prefixed with its exact line number, and the prompt forbids reporting on lines not in the PR's added-lines set. A server-side filter enforces the same constraint as a second guard, so no comment lands outside the diff.

**Security heuristics are non-negotiable.**
The prompt forces `critical` severity for dangerous patterns (`eval`, `exec`, `shell=True`, `pickle.loads` on untrusted data, SQL string-building) and `high` for hardcoded secrets.

**Async, background-processed.**
Review creation returns immediately with `pending`. The actual work runs in a FastAPI background task. The review moves through `pending → processing → completed/failed`, and failures are caught and persisted without crashing the worker.

---

## Running It Yourself

This is a **single-user, self-hosted** tool. There is no sign-up or multi-user access yet. To use it:

1. Clone this repository.
2. Create `.env` in the project root with your own keys:
   ```
   GITHUB_TOKEN=ghp_...      # needs `repo` scope
   GEMINI_API_KEY=...
   ```
3. Build and run:
   ```bash
   docker compose up --build
   ```
4. Open `http://localhost:8000/docs` and use `POST /reviews/` with your repository URL, `base_ref`, `head_ref`, and `pr_number`.

### About the hosted instance

The hosted deployment runs on the author's own `GITHUB_TOKEN` and `GEMINI_API_KEY` as a personal demo. Browsing `/docs` there is fine, but **reviews submitted against it will post comments from the author's GitHub account and bill the author's AI quota**. To use the tool for your own repositories, run your own instance as described above.

### Multi-user access (future)

Multi-user support is not implemented yet. The planned path is:

1. **User registration and authentication** — establishes user identity.
2. **Per-user credentials endpoint (BYOK)** — an authenticated user submits their own GitHub token and Gemini API key; keys are encrypted at rest, decrypted only when running that user's review, and never returned in plaintext.
3. **Token resolution order** — per-user credentials if present, otherwise the shared environment variables.

Until that exists, `.env` is the only supported way to supply credentials.

---

## Deployment

- Multi-stage Docker build (dependencies in a builder stage, slim runtime with `git` and `libstdc++` for `tiktoken`).
- Gunicorn + Uvicorn workers, unbuffered logs (`PYTHONUNBUFFERED=1`), healthcheck on `/health`.
- Deployed on AWS EC2 behind an Nginx reverse proxy.
- SQLite on a named Docker volume; a single Gunicorn worker (SQLite is single-writer).

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/reviews/` | Create a review (repo or PR mode) |
| `GET` | `/reviews/{id}` | Review status |
| `GET` | `/reviews/{id}/findings` | Findings for a review |
| `GET` | `/health` | Healthcheck |
| `GET` | `/docs` | Swagger UI |

---

## What's Done

- End-to-end PR review pipeline, validated against real PRs with inline comments posted.
- Symbol-level upstream context selection with token budgeting (Python).
- Prompt engineered for line grounding, upstream-only-when-genuine conflicts, and forced security severities.
- Two-layer guard against off-diff findings.
- Dockerized and deployed on AWS EC2 behind Nginx.
- Review state machine and failure handling.

---

## Future Improvements

- **User registration + authentication** — foundation for multi-user access.
- **Per-user credentials endpoint (BYOK)** — encrypted-at-rest storage of each user's GitHub token and Gemini key; decrypt only at review time; never return plaintext.
- **Job queue (Celery/RQ + Redis)** — BackgroundTasks dies if the worker restarts mid-review. A queue adds retries, persistence, and multi-worker safety.
- **Postgres** — SQLite is single-writer; Postgres unlocks multiple Gunicorn workers and proper migrations (Alembic).
- **Downstream impact analysis** — currently only upstream dependencies are included. A reverse import graph would show which callers are affected by a changed signature.
- **Elastic IP + domain + HTTPS (Certbot)** — currently reachable by public IP over HTTP.
- **Structured logging** — replace `print` with `logging` for levels and filtering.
- **Multi-language support** — chunking and import extraction are Python-only; JS/TS/JSX/TSX files are scanned but not parsed. A language-agnostic parser (e.g. tree-sitter) would extend coverage.
- **Stuck-review reconciliation on startup** — reviews interrupted mid-run currently remain in `processing`; a startup job will mark stale ones `failed`.

---

## Status

Functional and deployed. Suitable for personal use. The future items above are the path to a production-grade multi-user service.