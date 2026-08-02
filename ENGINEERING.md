# Engineering Standards — Repo-Pulse Lite

Этот документ отвечает на вопрос «как писать код в этом проекте?». За «что строим» см. `PRD.md`, за «почему приняты такие решения» — `ADR.md`.

## Frontend Standards

Preferred order:

1. HTML
2. Tailwind CSS
3. Native JavaScript
4. Alpine.js (только если чистого JS недостаточно для client-side состояния — фильтры, сортировка, toggles)

Forbidden:

- React
- Vue
- Angular
- Bootstrap
- jQuery
- htmx (не используется в v1 — весь датасет уже встроен в `report.html` на этапе генерации; см. PRD → Technology Stack, ADR-0003, ADR-0005)

## Backend Standards

**Environment:**

- uv

**Configuration:**

- python-dotenv

**Database:**

- SQLite

**HTTP:**

- httpx

**Tests:**

- pytest

**Rule**

Prefer Python stdlib before adding dependencies (см. ADR-0007 — Dependency Policy).
