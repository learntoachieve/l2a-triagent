"""Read-only JSON API + static web frontend for the Triagent ticket queue.

One FastAPI app serves both:

* ``GET /api/...`` — the scored, ranked issue queue as JSON. The ranking reuses
  ``triagent.db.queries`` (the same logic the Streamlit board reads), so the
  web UI and the board show identical data.
* ``/`` and other paths — the static single-page frontend in ``triagent/web``.

Read-only: no writes, no scoring, no LLM. Data access goes through an injectable
``IssueStore`` (FastAPI dependency ``get_store``) so tests can substitute a fake
and run with no live Postgres. Launch locally with::

    uvicorn triagent.api.app:app --reload

Then http://localhost:8000 shows the UI and http://localhost:8000/api/issues
returns JSON.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from triagent.db.connection import get_connection
from triagent.db.queries import load_issue_detail, load_ranked_issues

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


# --- response models -------------------------------------------------------


class Health(BaseModel):
    status: str


class IssueSummary(BaseModel):
    """One ranked row for the queue list. Score fields are null when unscored."""

    repo: str
    number: int
    title: str
    html_url: str
    state: str
    labels: list[str]
    source: str
    last_seen: datetime
    difficulty: str | None = None
    issue_type: str | None = None
    solvability: float | None = None
    skill_fit: float | None = None


class IssueDetail(IssueSummary):
    """Full detail for the detail view: adds the body and the latest rationale."""

    body: str | None = None
    rationale: str | None = None


# --- data access (injectable) ----------------------------------------------


class IssueStore(Protocol):
    """The read surface the API needs. Mocked in tests; backed by Postgres live."""

    def ranked(self) -> list[dict[str, Any]]: ...

    def detail(self, key: str) -> dict[str, Any] | None: ...


class DbIssueStore:
    """Default store: reads Postgres through the shared ranked-queue queries."""

    def ranked(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            return load_ranked_issues(conn)

    def detail(self, key: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            return load_issue_detail(conn, key)


def get_store() -> IssueStore:
    """FastAPI dependency. Overridden in tests via ``app.dependency_overrides``."""
    return DbIssueStore()


# --- filtering (mirrors the board's controls) ------------------------------


def filter_issues(
    issues: list[dict[str, Any]],
    *,
    min_solvability: float,
    difficulty: str | None,
    repo: str | None,
    q: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Apply the queue filters, preserving the most-solvable-first input order.

    ``min_solvability > 0`` drops unscored issues (their solvability is null),
    matching the board: ``(solvability or 0.0) >= min``.
    """
    rows = issues
    if repo:
        rows = [r for r in rows if r["repo"] == repo]
    if difficulty:
        rows = [r for r in rows if r["difficulty"] == difficulty]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r["title"].lower()]
    if min_solvability > 0.0:
        rows = [r for r in rows if (r["solvability"] or 0.0) >= min_solvability]
    return rows[:limit]


# --- app -------------------------------------------------------------------

app = FastAPI(title="Triagent API", description="Read-only ranked issue queue.")


@app.get("/api/health")
def health() -> Health:
    """Liveness check (used by the deploy card)."""
    return Health(status="ok")


@app.get("/api/issues")
def list_issues(
    store: IssueStore = Depends(get_store),
    min_solvability: float = Query(0.0, ge=0.0, le=1.0),
    difficulty: str | None = None,
    repo: str | None = None,
    q: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[IssueSummary]:
    """The ranked issue queue (most solvable first), with optional filters."""
    rows = filter_issues(
        store.ranked(),
        min_solvability=min_solvability,
        difficulty=difficulty,
        repo=repo,
        q=q,
        limit=limit,
    )
    return [IssueSummary(**r) for r in rows]


@app.get("/api/issues/{owner}/{repo}/{number}")
def issue_detail(
    owner: str,
    repo: str,
    number: int,
    store: IssueStore = Depends(get_store),
) -> IssueDetail:
    """One issue's full detail, keyed by ``owner/repo#number``."""
    key = f"{owner}/{repo}#{number}"
    row = store.detail(key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"issue not found: {key}")
    return IssueDetail(**row)


# Mount the static frontend LAST so the explicit /api routes above win. With
# html=True, "/" serves index.html. Skipped if the dir is missing (e.g. some
# test environments) so importing the app never fails.
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
