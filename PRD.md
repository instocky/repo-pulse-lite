# PRD - Repo-Pulse Lite v1

## Vision

Repo-Pulse Lite is a personal tool for daily monitoring of a user's GitHub starred repositories.
It should stay understandable for one developer after six months without extra architectural layers.

## Problem

GitHub does not provide historical star growth for someone else's repositories.
The user wants to:

- collect daily snapshots of starred repositories;
- inspect trend changes over time;
- find fast-growing projects;
- open the report locally without a web server.

## Goals

MVP must:

- read the starred repository list;
- collect a snapshot into SQLite;
- preserve history;
- build a static HTML dashboard from SQLite only.

## Non Goals

v1 does not include:

- FastAPI
- Jinja
- nginx
- systemd
- Repository Pattern
- DTO
- Service Layer
- Chart abstraction
- Web API
- auth
- notifications
- deployment automation

## Success Criteria

After setup, the user runs:

```bash
python main.py all
```

and gets:

```text
pulse.db
report.html
```

`python main.py snapshot` updates only `pulse.db`.
`python main.py report` builds `report.html` from the existing `pulse.db`.

## Constraints

- Python 3.11+
- SQLite
- Plotly
- GitHub REST API
- maximum 5 Python modules, plus `config.py`
- approximately <= 1000 LOC
- keep runtime dependencies minimal

## Technology Stack

### Backend

- Python 3.11+
- uv
- SQLite
- httpx
- Plotly
- python-dotenv

### Frontend

- Tailwind CSS (Play CDN)
- Native JavaScript (ES2022)
- Alpine.js for client-side filters, sorting, and toggles

The full dataset is embedded into `report.html` during generation (SQLite -> HTML), so filtering, sorting, and toggles run entirely on the client.
Report generation reads only SQLite and does not make extra HTTP requests to GitHub.

### Deployment

- local execution only
- no web server required
- static HTML output

## Scope v1

Collect:

- Stars
- Forks
- Watchers
- Open Issues
- Language
- Updated At
- Pushed At
- Latest Release

Show:

- Current Stars
- Today Delta
- 7-day Growth
- 30-day Growth
- Top Growing
- Recently Updated

## Directory

```text
repo-pulse-lite/
  README.md
  pyproject.toml
  main.py
  github.py
  db.py
  report.py
  config.py
  pulse.db
  report.html
```

## Definition of Done

The project is complete when:

- there are no more than 5 Python modules, plus `config.py`;
- runtime dependencies stay <= 15;
- `python main.py all` creates or updates `pulse.db` and `report.html`;
- `python main.py snapshot` creates or updates only `pulse.db`;
- `report.html` opens locally without a web server;
- report generation reads only SQLite and does not call GitHub again;
- the frontend uses Tailwind CSS plus Alpine.js for client-side filters, sorting, and toggles;
- no extra future-proof layers are introduced.
