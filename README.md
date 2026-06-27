# Triagent

Triagent is a ticket-triage trainer built on top of live GitHub issues. It pulls real, open
issues from public repositories, scores them for solvability and difficulty, and presents them as a
workable ticket queue so you can practice triaging and solving real-world work instead of toy
problems. This repository currently contains the project skeleton; ingestion, scoring, and the
agent are built in later phases.

## Quickstart

```powershell
# Create and activate a virtual environment
uv venv
.venv\Scripts\Activate.ps1

# Install the package with dev tooling
uv pip install -e ".[dev]"

# Run the three quality gates
ruff check .
mypy .
pytest -q
```

## Run the web app

The serve layer is a single FastAPI process that exposes the ranked queue as a read-only JSON API
**and** serves a custom web frontend (plain HTML/CSS/JS — no build step). One command runs both:

```powershell
uvicorn triagent.api.app:app --reload
```

Then open **http://localhost:8000** for the UI, while the API is available at the same origin:

- `GET /api/health` → `{"status": "ok"}`
- `GET /api/issues` → the ranked queue (filters: `min_solvability`, `difficulty`, `repo`, `q`, `limit`)
- `GET /api/issues/{owner}/{repo}/{number}` → one issue's full detail (with rationale + body)

The frontend reads the same data as the Streamlit board (shared ranking query) and calls the API via
relative URLs, so it works unchanged locally or when deployed. It's a read-only view — no scoring or
DB writes happen here.

## Project layout (target)

The structure below is the intended end state. Most directories do not exist yet — each is built in
its own phase. The phase tag (`[P#]`) marks when a part comes online.

```
triagent/
  config.py      # env secrets + config.toml tunables
  models.py      # Pydantic models: Issue, Score, Run, SolveLog
  db/            # connection helper + migration runner
  ingest/        # github_client, normalize, upsert      [P1]
  score/         # solvability + skill-fit scoring        [P2]
  classify/      # issue type + difficulty                [P2]
  eval/          # golden set + metrics harness           [P3]
  agent/         # LangGraph triage core                  [P4]
  api/           # FastAPI read layer                     [P5]
  web/           # custom static frontend (HTML/CSS/JS)   [P5]
  board/         # Streamlit ticket queue UI              [P5]
config.toml
tests/
docs/            # architecture.md, adr/
```
