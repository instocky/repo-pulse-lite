from __future__ import annotations

from typing import Any

import httpx

from config import Config


def fetch_starred(config: Config) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1

    with _client(config) as client:
        while True:
            print(f"Fetching starred page {page}")
            response = client.get(
                "/user/starred",
                params={"per_page": 100, "page": page},
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                return repos
            repos.extend(batch)
            page += 1


def _client(config: Config) -> httpx.Client:
    return httpx.Client(
        base_url=config.api_base_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {config.github_token}",
            "User-Agent": "repo-pulse-lite",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30.0,
    )
