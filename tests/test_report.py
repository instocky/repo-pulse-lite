from __future__ import annotations

from db import bootstrap, insert_snapshot
from report import FAVICON_ASSETS, write_report


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


def _seeded_db(database_path) -> None:
    bootstrap(database_path)
    insert_snapshot(
        database_path,
        [
            _repo(1, "octo/alpha", 10),
            _repo(2, "octo/bravo", 25),
        ],
    )


def test_write_report_publishes_favicons_next_to_the_html(workspace_tmp_path):
    """The report is served from a directory that is not the project root,
    so the icons must land next to the generated HTML or the browser shows
    a generic globe instead of the pulse mark.
    """
    database_path = workspace_tmp_path / "pulse.db"
    output_path = workspace_tmp_path / "index.html"
    _seeded_db(database_path)

    write_report(database_path, output_path)

    for name in FAVICON_ASSETS:
        published = output_path.parent / name
        assert published.exists(), f"{name} was not published next to the report"
        assert published.stat().st_size > 0, f"{name} was published empty"


def test_report_html_links_both_favicon_schemes(workspace_tmp_path):
    database_path = workspace_tmp_path / "pulse.db"
    output_path = workspace_tmp_path / "index.html"
    _seeded_db(database_path)

    write_report(database_path, output_path)
    html_text = output_path.read_text(encoding="utf-8")

    assert 'href="favicon.svg"' in html_text
    assert 'href="favicon-dark.svg"' in html_text
    assert 'media="(prefers-color-scheme: dark)"' in html_text
    assert 'href="favicon.ico"' in html_text
