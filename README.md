# Repo-Pulse Lite

Локальный инструмент для ежедневных snapshot'ов `starred`-репозиториев GitHub и генерации статического HTML-отчёта.

## Quick Start

### 1. Требования

- Python 3.11+
- GitHub token с доступом к `user:read`

### 2. Установка

Клонирование репозитория:

```bash
git clone <your-repo-url>
cd repo-pulse-lite
```

Создание виртуального окружения и установка зависимостей.

Linux/macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

Проект использует плоский набор top-level модулей. Для editable install в `pyproject.toml` уже явно прописан блок `tool.setuptools.py-modules`, поэтому `pip install -e .` должен проходить без дополнительной ручной настройки.

Проверка версии Python внутри окружения:

```bash
python --version
```

Ожидается `Python 3.11.x` или выше.

### 3. Конфигурация

Создайте `.env`:

```bash
cp .env.example .env
```

Пример содержимого:

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
- `report.html` — статический dashboard

Важно: `report.html` не полностью self-contained. Внутри используются внешние CDN-скрипты `cdn.tailwindcss.com` и `cdn.jsdelivr.net`, поэтому для полной работы интерфейса у клиента должен быть доступ в интернет.

## Deployment

Для развёртывания на Ubuntu 22.04 с Nginx, HTTPS и автоматизацией через Cron см. [deploy.md](deploy.md).

Ключевые моменты из production-установки:

- на Ubuntu 22.04 нужен именно Python 3.11+, а не системный Python 3.10;
- при деплое в существующую директорию используйте `git clone <your-repo-url> .`, иначе Git создаст вложенную папку;
- если деплой делается под `root`, то `.env`, `.venv` и cron дальше тоже будут обслуживаться от `root`.

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
