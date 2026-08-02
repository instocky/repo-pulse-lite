from __future__ import annotations

import httpx

from config import Config
from github import _client, fetch_starred


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200, url: str = "https://api.github.com/mock"):
        self.payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", url)
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self.payload


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, path, params=None):
        self.calls.append((path, params))
        return self.responses.pop(0)


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


def test_fetch_starred_enriches_latest_release_and_paginates(monkeypatch, workspace_tmp_path):
    config = Config(
        github_token="secret-token",
        database_path=workspace_tmp_path / "pulse.db",
        report_path=workspace_tmp_path / "report.html",
    )
    fake_client = _FakeClient(
        responses=[
            _FakeResponse([{"id": 1, "full_name": "octo/one"}]),
            _FakeResponse({"published_at": "2026-08-01T00:00:00Z"}),
            _FakeResponse([{"id": 2, "full_name": "octo/two"}]),
            _FakeResponse({}, status_code=404),
            _FakeResponse([]),
        ]
    )

    monkeypatch.setattr("github._client", lambda _: fake_client)

    repos = fetch_starred(config)

    assert repos == [
        {"id": 1, "full_name": "octo/one", "latest_release_published_at": "2026-08-01T00:00:00Z"},
        {"id": 2, "full_name": "octo/two", "latest_release_published_at": None},
    ]
    assert fake_client.calls == [
        ("/user/starred", {"per_page": 100, "page": 1}),
        ("/repos/octo/one/releases/latest", None),
        ("/user/starred", {"per_page": 100, "page": 2}),
        ("/repos/octo/two/releases/latest", None),
        ("/user/starred", {"per_page": 100, "page": 3}),
    ]
