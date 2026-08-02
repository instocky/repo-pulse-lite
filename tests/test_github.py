from __future__ import annotations

from config import Config
from github import _client, fetch_starred


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


class _FakeClient:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, path, params):
        self.calls.append((path, params))
        return _FakeResponse(self.pages.pop(0))


def test_client_uses_github_headers(workspace_tmp_path):
    config = Config(
        github_token="secret-token",
        database_path=workspace_tmp_path / "pulse.db",
        report_path=workspace_tmp_path / "report.html",
    )

    client = _client(config)

    assert str(client.base_url) == "https://api.github.com"
    assert client.headers["Authorization"] == "Bearer secret-token"
    assert client.headers["Accept"] == "application/vnd.github+json"
    assert client.headers["User-Agent"] == "repo-pulse-lite"
    assert client.headers["X-GitHub-Api-Version"] == "2022-11-28"
    client.close()


def test_fetch_starred_paginates_until_empty(monkeypatch, workspace_tmp_path):
    config = Config(
        github_token="secret-token",
        database_path=workspace_tmp_path / "pulse.db",
        report_path=workspace_tmp_path / "report.html",
    )
    fake_client = _FakeClient(
        pages=[
            [{"id": 1, "full_name": "octo/one"}],
            [{"id": 2, "full_name": "octo/two"}],
            [],
        ]
    )

    monkeypatch.setattr("github._client", lambda _: fake_client)

    repos = fetch_starred(config)

    assert repos == [
        {"id": 1, "full_name": "octo/one"},
        {"id": 2, "full_name": "octo/two"},
    ]
    assert fake_client.calls == [
        ("/user/starred", {"per_page": 100, "page": 1}),
        ("/user/starred", {"per_page": 100, "page": 2}),
        ("/user/starred", {"per_page": 100, "page": 3}),
    ]
