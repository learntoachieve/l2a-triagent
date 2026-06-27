"""Shared read queries for the scored issue queue.

The ranking logic (each issue LEFT JOINed to its single latest score, ordered
most-solvable-first with unscored last) lives here so the Streamlit board and
the FastAPI serve layer read the EXACT same data. Both call these functions;
neither re-implements the SQL.
"""

from __future__ import annotations

from typing import Any

import psycopg

Conn = psycopg.Connection[tuple[Any, ...]]

# Columns returned by the ranked-queue query, in SELECT order.
RANKED_COLUMNS = [
    "repo",
    "number",
    "title",
    "html_url",
    "state",
    "labels",
    "source",
    "last_seen",
    "solvability",
    "skill_fit",
    "difficulty",
    "issue_type",
]

# Each issue joined to its single latest score (by scored_at). Issues with no
# score yield NULL score columns. Highest solvability first; unscored last.
RANKED_ISSUES_SQL = """
SELECT i.repo, i.number, i.title, i.html_url, i.state, i.labels, i.source, i.last_seen,
       s.solvability, s.skill_fit, s.difficulty, s.issue_type
FROM issue i
LEFT JOIN LATERAL (
    SELECT solvability, skill_fit, difficulty, issue_type
    FROM score
    WHERE issue_key = i.key
    ORDER BY scored_at DESC
    LIMIT 1
) s ON true
ORDER BY s.solvability DESC NULLS LAST, i.last_seen DESC
"""

# One issue's full detail: the ranked columns plus the body and the latest
# score's rationale (NULL when unscored). Looked up by the natural key.
DETAIL_COLUMNS = [*RANKED_COLUMNS, "body", "rationale"]

DETAIL_SQL = """
SELECT i.repo, i.number, i.title, i.html_url, i.state, i.labels, i.source, i.last_seen,
       s.solvability, s.skill_fit, s.difficulty, s.issue_type,
       i.body, s.rationale
FROM issue i
LEFT JOIN LATERAL (
    SELECT solvability, skill_fit, difficulty, issue_type, rationale
    FROM score
    WHERE issue_key = i.key
    ORDER BY scored_at DESC
    LIMIT 1
) s ON true
WHERE i.key = %s
"""


def load_ranked_issues(conn: Conn) -> list[dict[str, Any]]:
    """All stored issues joined to their latest score, most solvable first."""
    rows = conn.execute(RANKED_ISSUES_SQL).fetchall()
    return [dict(zip(RANKED_COLUMNS, row, strict=True)) for row in rows]


def load_issue_detail(conn: Conn, key: str) -> dict[str, Any] | None:
    """One issue's full detail by natural key ("owner/name#number"), or None."""
    row = conn.execute(DETAIL_SQL, (key,)).fetchone()
    if row is None:
        return None
    return dict(zip(DETAIL_COLUMNS, row, strict=True))
