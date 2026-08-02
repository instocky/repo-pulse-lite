from __future__ import annotations

import sqlite3
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


def bootstrap(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(SCHEMA)


def insert_snapshot(database_path: Path, repos: list[dict[str, Any]]) -> str:
    snapshot_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = [_snapshot_row(snapshot_at, repo) for repo in repos]

    with sqlite3.connect(database_path) as connection:
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

    return snapshot_at


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
