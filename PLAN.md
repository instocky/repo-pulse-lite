# Plan — Repo-Pulse Lite v1

Тикеты построены вертикально: каждый выдаёт законченный пользовательский результат, а не только очередной архитектурный слой. После тикета 01 проект уже полезен.

## Tickets

### 01 — Snapshot → pulse.db (M)

Первая поставка сразу работает end-to-end.

```
scaffold (pyproject, sqlite init)
   ↓
fetch_starred() / fetch_repo()   [github.py]
   ↓
bootstrap() / insert_snapshot()  [db.py]
   ↓
CLI: python main.py snapshot
```

Результат: `pulse.db` с одним снимком starred-репозиториев.

### 02 — Report → report.html (M)

```
select_history()          [db.py]
   ↓
Current Stars (текущий срез)
   ↓
Plotly → report.html      [report.py]
   ↓
CLI: python main.py report
```

Результат: открываемый локально HTML с текущим состоянием.

### 03 — Growth Analytics (S)

```
SQL: today / 7d / 30d / top / recent
   ↓
добавляется в report.html
```

Результат: отчёт показывает динамику, а не только срез — закрывает ключевую Problem из PRD.

### 04 — CLI Polish (XS)

```
snapshot
report
all
```

где:

```
all
  ↓
snapshot
  ↓
report
```

Результат: одна команда для полного цикла (см. Success Criteria в PRD).

### 05 — Tests (S)

pytest, только:

- GitHub
- DB
- Analytics

### 06 — Documentation (XS)

README:

- Quick Start
- Архитектура

## Definition of Done (сводка)

- ≤ 5 python-модулей (+ `config.py` как служебный)
- ≤ 1000 LOC (без тестов и README)
- ≤ 15 runtime-зависимостей
- `report.html` cold start < 2 сек (из уже собранного `pulse.db`)
- `python main.py all` → `pulse.db` + `report.html`
- отчёт без веб-сервера и без доп. запросов к GitHub
- никаких DTO / Repository / Service Layer / Web Framework / Chart Abstraction
