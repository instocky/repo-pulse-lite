# Plan - Repo-Pulse Lite v1

Tickets are vertical slices: each one should produce a user-visible result, not another architecture layer.

## Tickets

### 01 - Snapshot -> pulse.db (M)

End-to-end first delivery:

```text
scaffold (pyproject, sqlite init)
  -> fetch_starred() [github.py]
  -> bootstrap() / insert_snapshot() [db.py]
  -> CLI: python main.py snapshot
```

Result: `pulse.db` with one snapshot of starred repositories.

### 02 - Report -> report.html (M)

```text
select_history() [db.py]
  -> current stars
  -> Plotly -> report.html [report.py]
  -> CLI: python main.py report
```

Result: a locally openable HTML report built from SQLite.

### 03 - Growth Analytics (S)

```text
SQL: today / 7d / 30d / top / recent
  -> report.html
```

Result: the report shows trends, not just the latest snapshot.

### 04 - CLI Polish (XS)

Commands:

- `python main.py snapshot` -> updates only `pulse.db`
- `python main.py report` -> builds `report.html` from the existing `pulse.db`
- `python main.py all` -> runs `snapshot`, then `report`

Result: one command for the full cycle.

### 05 - Tests (S)

Pytest coverage is limited to:

- GitHub
- DB
- Analytics

Completion criteria:

- `pytest` passes without collection errors
- imports work from the project root
- baseline scenarios for `github.py`, `db.py`, and analytics SQL are covered

### 06 - Documentation (XS)

Documentation covers:

- Quick Start
- Architecture
- CLI contract

## Definition of Done

- <= 5 Python modules, plus `config.py`
- <= 1000 LOC excluding tests and README
- <= 15 runtime dependencies
- `report.html` cold start < 2 seconds from an existing `pulse.db`
- `python main.py all` -> `pulse.db` + `report.html`
- `python main.py snapshot` -> only `pulse.db`
- report works without a web server and without extra GitHub requests
- report frontend uses Tailwind CSS + Alpine.js for client-side filters, sorting, and toggles
- no DTO / Repository / Service Layer / Web Framework / Chart Abstraction
