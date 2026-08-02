# PRD — Repo-Pulse Lite v1

## Vision

Repo-Pulse Lite — персональный инструмент для ежедневного мониторинга GitHub-репозиториев пользователя.

Проект должен оставаться понятным одному разработчику спустя полгода без документации и занимать не более одного экрана архитектуры.

## Problem

GitHub больше не предоставляет историю звёзд для чужих репозиториев.

Пользователь хочет:

- автоматически собирать ежедневные снимки своих starred-репозиториев;
- видеть динамику;
- находить быстрорастущие проекты.

Без VPS, FastAPI и лишней инфраструктуры.

## Goals

MVP должен уметь:

- читать список starred repos;
- собирать snapshot;
- хранить историю;
- строить HTML dashboard.

## Non Goals

v1 не содержит:

- FastAPI
- Jinja
- nginx
- systemd
- Repository Pattern
- DTO
- Service Layer
- Chart abstraction
- Web API
- авторизацию
- уведомления
- deployment automation

## Success Criteria

После установки пользователь выполняет:

```bash
python main.py snapshot
```

и получает:

```text
pulse.db
report.html
```

через несколько секунд.

## Constraints

- Python 3.11+
- SQLite
- Plotly
- GitHub REST API
- максимум 5 python-файлов
- максимум ~1000 LOC
- zero mandatory dependencies кроме необходимых

## Technology Stack

### Backend

- Python 3.11+
- uv (package & environment manager)
- SQLite
- httpx
- Plotly
- python-dotenv

### Frontend

- Tailwind CSS (Play CDN)
- Native JavaScript (ES2022)
- Alpine.js (client-side state — filters, sorting, toggles)

Весь датасет уже загружен в `report.html` на этапе генерации (SQLite → HTML), поэтому фильтрация и сортировка выполняются на клиенте без обращения к серверу. htmx исключён из v1: он оправдан только когда данные подгружаются с backend по действию пользователя, а в статичном отчёте такой сценарий отсутствует (см. ADR-0003, ADR-0005). Если появится реальная потребность в live-backend — это выходит за рамки Lite и относится к основному Repo-Pulse.

### Deployment

- Local execution
- No web server required
- Static HTML output

## Scope v1

**Собирать:**

- Stars
- Forks
- Watchers
- Open Issues
- Language
- Updated At
- Pushed At
- Latest Release

**Показывать:**

- Current Stars
- Today Delta
- 7-day Growth
- 30-day Growth
- Top Growing
- Recently Updated

## Directory

```
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

## Anti-Goals

Repo-Pulse Lite никогда не станет:

- FastAPI / Web API
- Microservices
- Plugin system
- Repository Pattern
- DDD
- Clean Architecture

Не потому, что это плохие практики — а потому что для них уже существует основной Repo-Pulse. Lite решает другую задачу.

## Definition of Done

Проект считается завершённым, если выполняются следующие условия:

- не более 5 Python-модулей (`config.py` допускается как шестой служебный файл);
- не более 1000 строк кода (без учёта тестов и `README`);
- не более 15 runtime-зависимостей;
- `report.html` открывается и рендерится из уже собранного `pulse.db` менее чем за 2 секунды (cold start; не относится к `snapshot`, так как он зависит от сетевых вызовов GitHub API);
- одна команда `python main.py all` создаёт/обновляет `pulse.db` и `report.html`;
- `report.html` открывается локально без веб-сервера;
- для генерации отчёта не требуется ни один дополнительный HTTP-запрос к GitHub — отчёт строится исключительно на основе данных в SQLite;
- отсутствуют слои, добавленные "на будущее" (DTO, Repository Pattern, Service Layer, Web Framework, Chart Abstraction и т.п.).

## Главная идея проекта

Repo-Pulse Lite — это не уменьшенная копия Repo-Pulse. Это эталон минимальной архитектуры, предназначенной для решения конкретной задачи с минимальным количеством кода.

Если новая функциональность требует заметного усложнения архитектуры, она относится к основному Repo-Pulse, а не к Lite.
