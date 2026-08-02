from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    github_token: str
    database_path: Path
    api_base_url: str = "https://api.github.com"


def load_config() -> Config:
    load_dotenv()

    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is required")

    database_path = Path(os.getenv("PULSE_DB", "pulse.db")).expanduser()
    return Config(github_token=github_token, database_path=database_path)
