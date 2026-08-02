from __future__ import annotations

import argparse

from config import load_config
from db import bootstrap, insert_snapshot
from github import fetch_starred


def main() -> None:
    parser = argparse.ArgumentParser(description="Repo-Pulse Lite")
    parser.add_argument("command", choices=["snapshot"])
    args = parser.parse_args()

    if args.command == "snapshot":
        run_snapshot()


def run_snapshot() -> None:
    config = load_config()
    bootstrap(config.database_path)

    starred = fetch_starred(config)
    print(f"Found {len(starred)} repositories")
    snapshot_at = insert_snapshot(config.database_path, starred)

    print(f"Saved {len(starred)} repos to {config.database_path} at {snapshot_at}")


if __name__ == "__main__":
    main()
