# Repo-Pulse Lite

Локальный инструмент для ежедневных snapshot'ов `starred`-репозиториев GitHub и генерации статического HTML-отчёта без веб-сервера.

## Quick Start

### 1. Требования

- Python 3.11+
- GitHub token с доступом к `user:read`

### 2. Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

### 3. Конфигурация

Создайте `.env`:

```env
GITHUB_TOKEN=ghp_xxx
PULSE_DB=pulse.db
PULSE_REPORT=report.html
```

Поддерживаемые переменные:

- `GITHUB_TOKEN` — обязателен для `snapshot`
- `PULSE_DB` — путь к SQLite-базе, по умолчанию `pulse.db`
- `PULSE_REPORT` — путь к HTML-отчёту, по умолчанию `report.html`

### 4. Команды

Снять snapshot:

```bash
python main.py snapshot
```

Собрать отчёт из уже сохранённых данных:

```bash
python main.py report
```

Полный цикл:

```bash
python main.py all
```

Результат:

- `pulse.db` — история snapshot'ов
- `report.html` — статический dashboard, открывается локально

## Architecture

Проект намеренно плоский: без DTO, service layer, repository pattern и web framework.

### Поток данных

```text
GitHub REST API
  -> github.py fetch_starred()
  -> db.py insert_snapshot()
  -> SQLite pulse.db
  -> db.py select_*()
  -> report.py write_report()
  -> report.html
```

### Модули

- `main.py` — CLI entrypoint: `snapshot`, `report`, `all`
- `config.py` — чтение `.env` и сборка `Config`
- `github.py` — загрузка `starred`-репозиториев через GitHub REST API
- `db.py` — schema, запись snapshot'ов, SQL-аналитика
- `report.py` — генерация статического HTML-отчёта и chart через Plotly

### Модель хранения

Все snapshot'ы лежат в одной таблице `snapshots`. Каждая строка — состояние одного репозитория в конкретный момент `snapshot_at`.

Это даёт:

- простой append-only storage;
- SQL-аналитику без дополнительных слоёв;
- генерацию отчёта полностью из SQLite, без повторных запросов к GitHub.

## Tests

```bash
pytest
```
