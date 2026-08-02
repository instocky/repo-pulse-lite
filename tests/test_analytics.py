from __future__ import annotations

import sqlite3
from contextlib import closing

from db import SCHEMA, select_latest_growth, select_recently_updated, select_top_growth


def test_growth_queries_calculate_today_7d_30d_and_recent_updates(workspace_tmp_path):
    database_path = workspace_tmp_path / "pulse.db"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(SCHEMA)
        rows = [
            (
                "2026-07-01T00:00:00+00:00",
                1,
                "octo/alpha",
                "alpha",
                "octo",
                "https://github.com/octo/alpha",
                "alpha repo",
                "Python",
                10,
                1,
                1,
                0,
                "2026-07-01T10:00:00+00:00",
                "2026-07-01T10:00:00+00:00",
                None,
            ),
            (
                "2026-07-25T00:00:00+00:00",
                1,
                "octo/alpha",
                "alpha",
                "octo",
                "https://github.com/octo/alpha",
                "alpha repo",
                "Python",
                15,
                1,
                1,
                0,
                "2026-07-25T10:00:00+00:00",
                "2026-07-25T10:00:00+00:00",
                None,
            ),
            (
                "2026-08-01T00:00:00+00:00",
                1,
                "octo/alpha",
                "alpha",
                "octo",
                "https://github.com/octo/alpha",
                "alpha repo",
                "Python",
                17,
                1,
                1,
                0,
                "2026-08-01T10:00:00+00:00",
                "2026-08-01T10:00:00+00:00",
                None,
            ),
            (
                "2026-08-02T00:00:00+00:00",
                1,
                "octo/alpha",
                "alpha",
                "octo",
                "https://github.com/octo/alpha",
                "alpha repo",
                "Python",
                20,
                1,
                1,
                0,
                "2026-08-02T10:00:00+00:00",
                "2026-08-02T11:00:00+00:00",
                None,
            ),
            (
                "2026-07-25T00:00:00+00:00",
                2,
                "octo/bravo",
                "bravo",
                "octo",
                "https://github.com/octo/bravo",
                "bravo repo",
                "Go",
                50,
                1,
                1,
                0,
                "2026-07-25T09:00:00+00:00",
                "2026-07-25T09:00:00+00:00",
                None,
            ),
            (
                "2026-08-01T00:00:00+00:00",
                2,
                "octo/bravo",
                "bravo",
                "octo",
                "https://github.com/octo/bravo",
                "bravo repo",
                "Go",
                55,
                1,
                1,
                0,
                "2026-08-01T09:00:00+00:00",
                "2026-08-01T09:00:00+00:00",
                None,
            ),
            (
                "2026-08-02T00:00:00+00:00",
                2,
                "octo/bravo",
                "bravo",
                "octo",
                "https://github.com/octo/bravo",
                "bravo repo",
                "Go",
                56,
                1,
                1,
                0,
                "2026-08-02T08:00:00+00:00",
                "2026-08-02T08:30:00+00:00",
                None,
            ),
        ]
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

    growth = select_latest_growth(database_path)
    top_growth = select_top_growth(database_path, limit=2)
    recent = select_recently_updated(database_path, limit=2)

    assert [row["full_name"] for row in growth] == ["octo/bravo", "octo/alpha"]

    alpha = next(row for row in growth if row["full_name"] == "octo/alpha")
    bravo = next(row for row in growth if row["full_name"] == "octo/bravo")

    assert alpha["today_delta"] == 3
    assert alpha["delta_7d"] == 5
    assert alpha["delta_30d"] == 10
    assert bravo["today_delta"] == 1
    assert bravo["delta_7d"] == 6
    assert bravo["delta_30d"] is None

    assert [row["full_name"] for row in top_growth] == ["octo/alpha", "octo/bravo"]
    assert [row["full_name"] for row in recent] == ["octo/alpha", "octo/bravo"]
