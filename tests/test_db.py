from __future__ import annotations

import sqlite3

from db import bootstrap, insert_snapshot, select_latest_snapshot


def _repo(repo_id: int, full_name: str, stars: int) -> dict[str, object]:
    owner, name = full_name.split("/", 1)
    return {
        "id": repo_id,
        "full_name": full_name,
        "name": name,
        "owner": {"login": owner},
        "html_url": f"https://github.com/{full_name}",
        "description": f"{full_name} description",
        "language": "Python",
        "stargazers_count": stars,
        "forks_count": repo_id,
        "watchers_count": repo_id + 10,
        "open_issues_count": repo_id + 20,
        "updated_at": "2026-08-01T12:00:00+00:00",
        "pushed_at": "2026-08-01T13:00:00+00:00",
        "latest_release_published_at": "2026-07-31T09:00:00+00:00",
    }


def test_bootstrap_and_select_latest_snapshot_orders_by_stars(workspace_tmp_path):
    database_path = workspace_tmp_path / "pulse.db"

    bootstrap(database_path)
    insert_snapshot(
        database_path,
        [
            _repo(1, "octo/alpha", 10),
            _repo(2, "octo/bravo", 25),
        ],
    )

    rows = select_latest_snapshot(database_path)

    assert [row["full_name"] for row in rows] == ["octo/bravo", "octo/alpha"]
    assert rows[0]["stargazers_count"] == 25
    assert rows[0]["owner_login"] == "octo"


def test_insert_snapshot_rejects_duplicate_repo_within_same_timestamp(workspace_tmp_path, monkeypatch):
    database_path = workspace_tmp_path / "pulse.db"
    bootstrap(database_path)

    class _FrozenDateTime:
        @staticmethod
        def now(_tz):
            from datetime import datetime, timezone

            return datetime(2026, 8, 2, 10, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("db.datetime", _FrozenDateTime)

    insert_snapshot(database_path, [_repo(1, "octo/alpha", 10)])

    try:
        insert_snapshot(database_path, [_repo(1, "octo/alpha", 11)])
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Expected UNIQUE constraint violation for duplicate snapshot row")
