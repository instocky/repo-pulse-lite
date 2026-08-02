from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_at TEXT NOT NULL,
    repo_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_login TEXT NOT NULL,
    html_url TEXT NOT NULL,
    description TEXT,
    language TEXT,
    stargazers_count INTEGER NOT NULL,
    forks_count INTEGER NOT NULL,
    watchers_count INTEGER NOT NULL,
    open_issues_count INTEGER NOT NULL,
    updated_at TEXT,
    pushed_at TEXT,
    latest_release_published_at TEXT,
    UNIQUE(snapshot_at, repo_id)
);
"""


GROWTH_CTES = """
WITH latest_at AS (
    SELECT MAX(snapshot_at) AS snapshot_at
    FROM snapshots
),
previous_at AS (
    SELECT MAX(snapshot_at) AS snapshot_at
    FROM snapshots
    WHERE snapshot_at < (SELECT snapshot_at FROM latest_at)
),
week_at AS (
    SELECT MAX(snapshot_at) AS snapshot_at
    FROM snapshots
    WHERE julianday(snapshot_at) <= (
        SELECT julianday(snapshot_at) - 7
        FROM latest_at
    )
),
month_at AS (
    SELECT MAX(snapshot_at) AS snapshot_at
    FROM snapshots
    WHERE julianday(snapshot_at) <= (
        SELECT julianday(snapshot_at) - 30
        FROM latest_at
    )
)
"""


def bootstrap(database_path: Path) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(SCHEMA)


def insert_snapshot(database_path: Path, repos: list[dict[str, Any]]) -> str:
    snapshot_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = [_snapshot_row(snapshot_at, repo) for repo in repos]

    with closing(sqlite3.connect(database_path)) as connection:
        connection.executemany(
            """
            INSERT INTO snapshots (
                snapshot_at,
                repo_id,
                full_name,
                name,
                owner_login,
                html_url,
                description,
                language,
                stargazers_count,
                forks_count,
                watchers_count,
                open_issues_count,
                updated_at,
                pushed_at,
                latest_release_published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    return snapshot_at


def select_latest_snapshot(database_path: Path) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                snapshot_at,
                repo_id,
                full_name,
                name,
                owner_login,
                html_url,
                description,
                language,
                stargazers_count,
                forks_count,
                watchers_count,
                open_issues_count,
                updated_at,
                pushed_at,
                latest_release_published_at
            FROM snapshots
            WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM snapshots)
            ORDER BY stargazers_count DESC, full_name ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def select_latest_growth(database_path: Path) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            {GROWTH_CTES}
            SELECT
                latest.snapshot_at,
                latest.repo_id,
                latest.full_name,
                latest.name,
                latest.owner_login,
                latest.html_url,
                latest.description,
                latest.language,
                latest.stargazers_count,
                latest.forks_count,
                latest.watchers_count,
                latest.open_issues_count,
                latest.updated_at,
                latest.pushed_at,
                latest.latest_release_published_at,
                latest.stargazers_count - COALESCE(previous.stargazers_count, latest.stargazers_count) AS today_delta,
                CASE
                    WHEN week.snapshot_at IS NULL THEN NULL
                    ELSE latest.stargazers_count - week.stargazers_count
                END AS delta_7d,
                CASE
                    WHEN month.snapshot_at IS NULL THEN NULL
                    ELSE latest.stargazers_count - month.stargazers_count
                END AS delta_30d
            FROM snapshots AS latest
            LEFT JOIN snapshots AS previous
                ON previous.repo_id = latest.repo_id
               AND previous.snapshot_at = (SELECT snapshot_at FROM previous_at)
            LEFT JOIN snapshots AS week
                ON week.repo_id = latest.repo_id
               AND week.snapshot_at = (SELECT snapshot_at FROM week_at)
            LEFT JOIN snapshots AS month
                ON month.repo_id = latest.repo_id
               AND month.snapshot_at = (SELECT snapshot_at FROM month_at)
            WHERE latest.snapshot_at = (SELECT snapshot_at FROM latest_at)
            ORDER BY latest.stargazers_count DESC, latest.full_name ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def select_top_growth(database_path: Path, limit: int = 10) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            {GROWTH_CTES}
            SELECT
                latest.full_name,
                latest.html_url,
                latest.stargazers_count,
                latest.stargazers_count - COALESCE(previous.stargazers_count, latest.stargazers_count) AS today_delta,
                CASE
                    WHEN week.snapshot_at IS NULL THEN NULL
                    ELSE latest.stargazers_count - week.stargazers_count
                END AS delta_7d,
                CASE
                    WHEN month.snapshot_at IS NULL THEN NULL
                    ELSE latest.stargazers_count - month.stargazers_count
                END AS delta_30d
            FROM snapshots AS latest
            LEFT JOIN snapshots AS previous
                ON previous.repo_id = latest.repo_id
               AND previous.snapshot_at = (SELECT snapshot_at FROM previous_at)
            LEFT JOIN snapshots AS week
                ON week.repo_id = latest.repo_id
               AND week.snapshot_at = (SELECT snapshot_at FROM week_at)
            LEFT JOIN snapshots AS month
                ON month.repo_id = latest.repo_id
               AND month.snapshot_at = (SELECT snapshot_at FROM month_at)
            WHERE latest.snapshot_at = (SELECT snapshot_at FROM latest_at)
            ORDER BY
                COALESCE(
                    CASE WHEN delta_30d > 0 THEN delta_30d END,
                    CASE WHEN delta_7d > 0 THEN delta_7d END,
                    CASE WHEN today_delta > 0 THEN today_delta END,
                    0
                ) DESC,
                latest.stargazers_count DESC,
                latest.full_name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def select_recently_updated(database_path: Path, limit: int = 10) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                full_name,
                html_url,
                pushed_at,
                updated_at,
                language,
                stargazers_count
            FROM snapshots
            WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM snapshots)
            ORDER BY COALESCE(pushed_at, updated_at) DESC, full_name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def _snapshot_row(snapshot_at: str, repo: dict[str, Any]) -> tuple[Any, ...]:
    owner = repo.get("owner") or {}
    return (
        snapshot_at,
        repo["id"],
        repo["full_name"],
        repo["name"],
        owner["login"],
        repo["html_url"],
        repo.get("description"),
        repo.get("language"),
        repo["stargazers_count"],
        repo["forks_count"],
        repo["watchers_count"],
        repo["open_issues_count"],
        repo.get("updated_at"),
        repo.get("pushed_at"),
        repo.get("latest_release_published_at"),
    )
