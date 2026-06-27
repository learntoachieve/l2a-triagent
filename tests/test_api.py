"""Offline tests for the read-only serve API.

No live Postgres and no network: the FastAPI ``get_store`` dependency is
overridden with an in-memory fake, so these exercise the endpoints, the
response shapes, and the filter logic without a database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from triagent.api.app import app, filter_issues, get_store

_NOW = datetime(2026, 6, 27, tzinfo=timezone.utc)


def _issue(
    repo: str,
    number: int,
    *,
    solvability: float | None,
    difficulty: str | None,
    title: str = "t",
) -> dict[str, Any]:
    return {
        "repo": repo,
        "number": number,
        "title": title,
        "html_url": f"https://github.com/{repo}/issues/{number}",
        "state": "open",
        "labels": ["bug"],
        "source": "search",
        "last_seen": _NOW,
        "solvability": solvability,
        "skill_fit": None if solvability is None else 0.5,
        "difficulty": difficulty,
        "issue_type": None if solvability is None else "bug",
    }


# Already in most-solvable-first order (as the SQL would return them).
_RANKED = [
    _issue("acme/web", 1, solvability=0.9, difficulty="easy", title="Add a unit test"),
    _issue("acme/api", 2, solvability=0.4, difficulty="hard", title="Refactor parser"),
    _issue("acme/web", 3, solvability=None, difficulty=None, title="Unscored thing"),
]


class _FakeStore:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def ranked(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def detail(self, key: str) -> dict[str, Any] | None:
        for r in self._rows:
            if f"{r['repo']}#{r['number']}" == key:
                return {**r, "body": "the body", "rationale": "because reasons"}
        return None


def _client(rows: list[dict[str, Any]] | None = None) -> TestClient:
    store = _FakeStore(_RANKED if rows is None else rows)
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_health() -> None:
    client = _client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    app.dependency_overrides.clear()


def test_list_issues_shape_and_order() -> None:
    client = _client()
    resp = client.get("/api/issues")
    assert resp.status_code == 200
    data = resp.json()
    assert [d["number"] for d in data] == [1, 2, 3]  # input order preserved
    first = data[0]
    expected = {
        "repo", "number", "title", "html_url", "state", "labels", "source",
        "last_seen", "difficulty", "issue_type", "solvability", "skill_fit",
    }
    assert expected <= set(first)
    assert first["solvability"] == 0.9
    app.dependency_overrides.clear()


def test_min_solvability_drops_lower_and_unscored() -> None:
    client = _client()
    resp = client.get("/api/issues", params={"min_solvability": 0.5})
    assert resp.status_code == 200
    nums = [d["number"] for d in resp.json()]
    assert nums == [1]  # 0.4 and the unscored row are filtered out
    app.dependency_overrides.clear()


def test_difficulty_filter() -> None:
    client = _client()
    resp = client.get("/api/issues", params={"difficulty": "hard"})
    assert [d["number"] for d in resp.json()] == [2]
    app.dependency_overrides.clear()


def test_repo_and_search_filters() -> None:
    client = _client()
    assert [d["number"] for d in client.get("/api/issues", params={"repo": "acme/web"}).json()] == [1, 3]
    assert [d["number"] for d in client.get("/api/issues", params={"q": "parser"}).json()] == [2]
    app.dependency_overrides.clear()


def test_limit() -> None:
    client = _client()
    resp = client.get("/api/issues", params={"limit": 2})
    assert len(resp.json()) == 2
    app.dependency_overrides.clear()


def test_detail_found_includes_body_and_rationale() -> None:
    client = _client()
    resp = client.get("/api/issues/acme/web/1")
    assert resp.status_code == 200
    d = resp.json()
    assert d["repo"] == "acme/web"
    assert d["number"] == 1
    assert d["body"] == "the body"
    assert d["rationale"] == "because reasons"
    app.dependency_overrides.clear()


def test_detail_missing_returns_404() -> None:
    client = _client()
    resp = client.get("/api/issues/acme/web/999")
    assert resp.status_code == 404
    app.dependency_overrides.clear()


def test_filter_issues_unit_keeps_unscored_at_zero_min() -> None:
    # min_solvability == 0 keeps unscored rows; > 0 drops them.
    kept = filter_issues(
        _RANKED, min_solvability=0.0, difficulty=None, repo=None, q=None, limit=100
    )
    assert len(kept) == 3
    dropped = filter_issues(
        _RANKED, min_solvability=0.01, difficulty=None, repo=None, q=None, limit=100
    )
    assert [r["number"] for r in dropped] == [1, 2]
