from __future__ import annotations

from html import escape
from pathlib import Path
from statistics import mean
from typing import Any

from db import select_latest_snapshot


def write_report(database_path: Path, output_path: Path) -> int:
    rows = select_latest_snapshot(database_path)
    if not rows:
        raise RuntimeError("No snapshots found. Run `python main.py snapshot` first.")

    figure_html = _build_chart(rows)
    output_path.write_text(_build_html(rows, figure_html), encoding="utf-8")
    return len(rows)


def _build_chart(rows: list[dict[str, Any]]) -> str:
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise RuntimeError("Plotly is required for `report`. Install project dependencies first.") from exc

    top_rows = rows[:15]
    figure = go.Figure(
        go.Bar(
            x=[row["stargazers_count"] for row in top_rows],
            y=[row["full_name"] for row in top_rows],
            orientation="h",
            marker_color="#2563eb",
            hovertemplate="%{y}<br>Stars: %{x}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Top Repositories by Stars",
        template="plotly_white",
        height=max(480, len(top_rows) * 36),
        margin={"l": 24, "r": 24, "t": 56, "b": 24},
        xaxis_title="Stars",
        yaxis_title="",
    )
    figure.update_yaxes(autorange="reversed")
    return figure.to_html(full_html=False, include_plotlyjs=True)


def _build_html(rows: list[dict[str, Any]], figure_html: str) -> str:
    snapshot_at = rows[0]["snapshot_at"]
    total_stars = sum(row["stargazers_count"] for row in rows)
    avg_stars = round(mean(row["stargazers_count"] for row in rows), 1)
    top_repo = rows[0]
    table_rows = "\n".join(_build_table_row(row) for row in rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Repo-Pulse Lite Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --panel: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --line: #cbd5e1;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, #dbeafe 0, transparent 28%),
        linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
    }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 48px; }}
    h1, h2 {{ margin: 0; }}
    p {{ margin: 0; color: var(--muted); }}
    .hero {{
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid rgba(148, 163, 184, 0.35);
      border-radius: 24px;
      padding: 28px;
      backdrop-filter: blur(12px);
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
    }}
    .meta {{ margin-top: 8px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px;
      margin: 24px 0;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
    }}
    .card {{ padding: 18px 20px; }}
    .card strong {{ display: block; font-size: 1.8rem; margin-bottom: 6px; }}
    .panel {{ margin-top: 20px; padding: 20px; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ padding: 12px 10px; border-top: 1px solid #e2e8f0; text-align: left; }}
    th {{ font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .description {{
      max-width: 420px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    @media (max-width: 720px) {{
      main {{ padding: 20px 14px 32px; }}
      .hero, .panel {{ padding: 16px; border-radius: 16px; }}
      th:nth-child(4), td:nth-child(4),
      th:nth-child(5), td:nth-child(5) {{ display: none; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Repo-Pulse Lite</h1>
      <p class="meta">Snapshot at {escape(snapshot_at)}</p>
      <div class="grid">
        <article class="card">
          <strong>{len(rows)}</strong>
          <p>Starred repositories</p>
        </article>
        <article class="card">
          <strong>{total_stars:,}</strong>
          <p>Total stars across current snapshot</p>
        </article>
        <article class="card">
          <strong>{avg_stars:,}</strong>
          <p>Average stars per repository</p>
        </article>
        <article class="card">
          <strong>{escape(top_repo["full_name"])}</strong>
          <p>Top repository with {top_repo["stargazers_count"]:,} stars</p>
        </article>
      </div>
    </section>
    <section class="panel">
      <h2>Current Stars</h2>
      <p>Top 15 repositories by current star count.</p>
      {figure_html}
    </section>
    <section class="panel">
      <h2>Snapshot Table</h2>
      <p>Current repository state loaded directly from SQLite.</p>
      <table>
        <thead>
          <tr>
            <th>Repository</th>
            <th>Stars</th>
            <th>Language</th>
            <th>Updated</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def _build_table_row(row: dict[str, Any]) -> str:
    description = row["description"] or ""
    language = row["language"] or "-"
    updated_at = row["updated_at"] or "-"
    return (
        "<tr>"
        f"<td><a href=\"{escape(row['html_url'])}\">{escape(row['full_name'])}</a></td>"
        f"<td>{row['stargazers_count']:,}</td>"
        f"<td>{escape(language)}</td>"
        f"<td>{escape(updated_at)}</td>"
        f"<td class=\"description\">{escape(description)}</td>"
        "</tr>"
    )
