from __future__ import annotations

import argparse

from config import load_config
from db import bootstrap, insert_snapshot
from github import fetch_starred
from report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Repo-Pulse Lite")
    parser.add_argument("command", choices=["snapshot", "report", "all"])
    args = parser.parse_args()

    if args.command == "snapshot":
        run_snapshot()
    elif args.command == "report":
        run_report()
    else:
        run_all()


def run_snapshot() -> None:
    config = load_config()
    if not config.github_token:
        raise RuntimeError("GITHUB_TOKEN is required for snapshot")

    bootstrap(config.database_path)

    starred = fetch_starred(config)
    print(f"Found {len(starred)} repositories")
    snapshot_at = insert_snapshot(config.database_path, starred)

    print(f"Saved {len(starred)} repos to {config.database_path} at {snapshot_at}")


def run_report() -> None:
    config = load_config()
    repo_count = write_report(config.database_path, config.report_path)
    print(f"Saved report for {repo_count} repos to {config.report_path}")


def run_all() -> None:
    run_snapshot()
    run_report()


if __name__ == "__main__":
    main()
