from __future__ import annotations

import html
import json
from pathlib import Path
from statistics import mean
import subprocess
from typing import Any

from db import select_latest_growth, select_recently_updated, select_top_growth


def write_report(database_path: Path, output_path: Path) -> int:
    rows = select_latest_growth(database_path)
    if not rows:
        raise RuntimeError("No snapshots found. Run `python main.py snapshot` first.")

    top_growth = select_top_growth(database_path)
    recent_updates = select_recently_updated(database_path)
    figure_html = _build_chart(rows)
    output_path.write_text(
        _build_html(rows, top_growth, recent_updates, figure_html),
        encoding="utf-8",
    )
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
            marker_color="#ea580c",
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


def _build_html(
    rows: list[dict[str, Any]],
    top_growth: list[dict[str, Any]],
    recent_updates: list[dict[str, Any]],
    figure_html: str,
) -> str:
    snapshot_at = rows[0]["snapshot_at"]
    total_stars = sum(row["stargazers_count"] for row in rows)
    avg_stars = round(mean(row["stargazers_count"] for row in rows), 1)
    top_repo = rows[0]
    total_today = sum(row["today_delta"] for row in rows)
    total_7d = _sum_optional(rows, "delta_7d")
    total_30d = _sum_optional(rows, "delta_30d")
    tooltip_title = ""
    git_metadata = _read_git_metadata()
    if git_metadata is not None:
        tooltip_lines = [
            f"Branch: {git_metadata['branch']}",
            f"Commit: {git_metadata['commit']}",
            f"Commit Date: {git_metadata['committed_at']}",
        ]
        tooltip_title = html.escape("\n".join(tooltip_lines), quote=True)
    payload = json.dumps(
        {
            "rows": rows,
            "top_growth": top_growth,
            "recent_updates": recent_updates,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Repo-Pulse Lite Report</title>
  <script src=\"https://cdn.tailwindcss.com\"></script>
  <script defer src=\"https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js\"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            ink: \"#0f172a\",
            pine: \"#15803d\",
            clay: \"#9a3412\",
          }},
          boxShadow: {{
            panel: \"0 20px 50px rgba(15, 23, 42, 0.08)\",
          }},
        }},
      }},
    }};

    function repoPulseReport(payload) {{
      return {{
        rows: payload.rows,
        topGrowth: payload.top_growth,
        recentUpdates: payload.recent_updates,
        search: \"\",
        language: \"all\",
        sort: \"stars_desc\",
        showGrowth: true,
        showRecent: true,
        get languages() {{
          return [...new Set(this.rows.map((row) => row.language).filter(Boolean))].sort();
        }},
        get filteredRows() {{
          const term = this.search.trim().toLowerCase();
          const items = this.rows.filter((row) => {{
            const matchesSearch =
              !term ||
              row.full_name.toLowerCase().includes(term) ||
              (row.description || \"\").toLowerCase().includes(term);
            const matchesLanguage = this.language === \"all\" || (row.language || \"Unknown\") === this.language;
            return matchesSearch && matchesLanguage;
          }});
          return items.sort((left, right) => this.compareRows(left, right));
        }},
        compareRows(left, right) {{
          if (this.sort === \"growth_desc\") {{
            return this.bestDelta(right) - this.bestDelta(left) || right.stargazers_count - left.stargazers_count;
          }}
          if (this.sort === \"updated_desc\") {{
            return (right.updated_at || \"\").localeCompare(left.updated_at || \"\") || left.full_name.localeCompare(right.full_name);
          }}
          return right.stargazers_count - left.stargazers_count || left.full_name.localeCompare(right.full_name);
        }},
        bestDelta(row) {{
          return row.delta_30d ?? row.delta_7d ?? row.today_delta ?? -1;
        }},
        deltaClass(value) {{
          if (value === null || value === undefined) return \"text-clay\";
          if (value === 0) return \"text-slate-500\";
          return \"text-pine\";
        }},
        deltaText(value) {{
          if (value === null || value === undefined) return \"n/a\";
          return `${{value >= 0 ? \"+\" : \"\"}}${{value.toLocaleString()}}`;
        }},
      }};
    }}
  </script>
</head>
<body class=\"min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(251,146,60,0.22),_transparent_22%),linear-gradient(180deg,_#fff7ed_0%,_#f8fafc_45%,_#ecfeff_100%)] text-ink\">
  <script id=\"report-data\" type=\"application/json\">{payload}</script>
  <main
    x-data=\"repoPulseReport(JSON.parse(document.getElementById('report-data').textContent))\"
    class=\"mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8\"
  >
    <section class=\"overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur md:p-8\">
      <div class=\"flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between\">
        <div class=\"max-w-3xl\">
          <span class=\"inline-flex rounded-full bg-orange-100 px-3 py-1 text-sm font-semibold text-orange-700\">Growth analytics</span>
          <h1 class=\"mt-4 text-4xl font-black tracking-tight text-slate-950 sm:text-5xl\" title=\"{tooltip_title}\">Repo-Pulse Lite</h1>
          <p class=\"mt-3 max-w-2xl text-base text-slate-600 sm:text-lg\">
            Snapshot at {snapshot_at}. The full dataset is embedded in this file, so filtering and sorting stay client-side.
          </p>
        </div>
        <div class=\"grid min-w-full gap-3 sm:grid-cols-2 lg:min-w-[22rem]\">
          <button
            type=\"button\"
            @click=\"showGrowth = !showGrowth\"
            class=\"rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-left text-sm font-semibold text-orange-900 transition hover:-translate-y-0.5 hover:bg-orange-100\"
          >
            Top Growing
            <span class=\"mt-1 block text-xs font-medium text-orange-700\" x-text=\"showGrowth ? 'Visible' : 'Hidden'\"></span>
          </button>
          <button
            type=\"button\"
            @click=\"showRecent = !showRecent\"
            class=\"rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-left text-sm font-semibold text-cyan-900 transition hover:-translate-y-0.5 hover:bg-cyan-100\"
          >
            Recently Updated
            <span class=\"mt-1 block text-xs font-medium text-cyan-700\" x-text=\"showRecent ? 'Visible' : 'Hidden'\"></span>
          </button>
        </div>
      </div>

      <div class=\"mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4\">
        <article class=\"rounded-3xl border border-slate-200 bg-slate-50 p-5\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-slate-500\">Repos</p>
          <p class=\"mt-4 text-3xl font-black text-slate-950\">{len(rows)}</p>
          <p class=\"mt-2 text-sm text-slate-600\">Starred repositories in the latest snapshot.</p>
        </article>
        <article class=\"rounded-3xl border border-slate-200 bg-white p-5\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-slate-500\">Total Stars</p>
          <p class=\"mt-4 text-3xl font-black text-slate-950\">{total_stars:,}</p>
          <p class=\"mt-2 text-sm text-slate-600\">Combined stars across the current portfolio.</p>
        </article>
        <article class=\"rounded-3xl border border-slate-200 bg-white p-5\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-slate-500\">Average</p>
          <p class=\"mt-4 text-3xl font-black text-slate-950\">{avg_stars:,}</p>
          <p class=\"mt-2 text-sm text-slate-600\">Average stars per repository.</p>
        </article>
        <article class=\"rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-slate-300\">Leader</p>
          <p class=\"mt-4 text-2xl font-black\">{top_repo["full_name"]}</p>
          <p class=\"mt-2 text-sm text-slate-300\">{top_repo["stargazers_count"]:,} stars right now.</p>
        </article>
      </div>

      <div class=\"mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4\">
        <article class=\"rounded-3xl border border-emerald-200 bg-emerald-50 p-5\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-emerald-700\">Today</p>
          <p class=\"mt-4 text-3xl font-black text-emerald-900\">{_format_delta(total_today)}</p>
          <p class=\"mt-2 text-sm text-emerald-800\">Change versus the previous snapshot.</p>
        </article>
        <article class=\"rounded-3xl border border-orange-200 bg-orange-50 p-5\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-orange-700\">7 Days</p>
          <p class=\"mt-4 text-3xl font-black text-orange-900\">{_format_optional_delta(total_7d)}</p>
          <p class=\"mt-2 text-sm text-orange-800\">Aggregate weekly growth.</p>
        </article>
        <article class=\"rounded-3xl border border-cyan-200 bg-cyan-50 p-5\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-cyan-700\">30 Days</p>
          <p class=\"mt-4 text-3xl font-black text-cyan-900\">{_format_optional_delta(total_30d)}</p>
          <p class=\"mt-2 text-sm text-cyan-800\">Aggregate monthly growth.</p>
        </article>
        <article class=\"rounded-3xl border border-slate-200 bg-white p-5\">
          <p class=\"text-sm font-medium uppercase tracking-[0.18em] text-slate-500\">Fastest Mover</p>
          <p class=\"mt-4 text-2xl font-black text-slate-950\">{top_growth[0]["full_name"] if top_growth else "-"}</p>
          <p class=\"mt-2 text-sm text-slate-600\">{_format_best_delta(top_growth[0]) if top_growth else "n/a"} by the best available window.</p>
        </article>
      </div>
    </section>

    <section class=\"mt-6 rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-panel\">
      <div class=\"flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between\">
        <div>
          <h2 class=\"text-2xl font-black text-slate-950\">Snapshot Explorer</h2>
          <p class=\"mt-2 text-sm text-slate-600\">Tailwind layout, Alpine state, and client-side filters over the embedded SQLite export.</p>
        </div>
        <div class=\"grid gap-3 md:grid-cols-3\">
          <label class=\"block\">
            <span class=\"mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500\">Search</span>
            <input
              x-model=\"search\"
              type=\"search\"
              placeholder=\"repo or description\"
              class=\"w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none ring-0 transition focus:border-orange-300 focus:bg-white\"
            >
          </label>
          <label class=\"block\">
            <span class=\"mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500\">Language</span>
            <select
              x-model=\"language\"
              class=\"w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-orange-300 focus:bg-white\"
            >
              <option value=\"all\">All languages</option>
              <template x-for=\"item in languages\" :key=\"item\">
                <option :value=\"item\" x-text=\"item\"></option>
              </template>
            </select>
          </label>
          <label class=\"block\">
            <span class=\"mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500\">Sort</span>
            <select
              x-model=\"sort\"
              class=\"w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-orange-300 focus:bg-white\"
            >
              <option value=\"stars_desc\">Stars</option>
              <option value=\"growth_desc\">Growth</option>
              <option value=\"updated_desc\">Updated</option>
            </select>
          </label>
        </div>
      </div>

      <div class=\"mt-6 overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white\">
        <div class=\"border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600\">
          <span x-text=\"filteredRows.length + ' repos visible'\"></span>
        </div>
        <div class=\"overflow-x-auto\">
          <table class=\"min-w-full divide-y divide-slate-200 text-sm\">
            <thead class=\"bg-white\">
              <tr class=\"text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500\">
                <th class=\"px-4 py-3\">Repository</th>
                <th class=\"px-4 py-3\">Stars</th>
                <th class=\"px-4 py-3\">Today</th>
                <th class=\"px-4 py-3\">7d</th>
                <th class=\"px-4 py-3\">30d</th>
                <th class=\"px-4 py-3\">Language</th>
                <th class=\"px-4 py-3\">Updated</th>
                <th class=\"px-4 py-3\">Description</th>
              </tr>
            </thead>
            <tbody class=\"divide-y divide-slate-100\">
              <template x-for=\"row in filteredRows\" :key=\"row.repo_id\">
                <tr class=\"align-top\">
                  <td class=\"px-4 py-4\">
                    <a :href=\"row.html_url\" class=\"font-semibold text-slate-950 hover:text-orange-700\" x-text=\"row.full_name\"></a>
                  </td>
                  <td class=\"px-4 py-4 text-slate-700\" x-text=\"row.stargazers_count.toLocaleString()\"></td>
                  <td class=\"px-4 py-4 font-semibold\" :class=\"deltaClass(row.today_delta)\" x-text=\"deltaText(row.today_delta)\"></td>
                  <td class=\"px-4 py-4 font-semibold\" :class=\"deltaClass(row.delta_7d)\" x-text=\"deltaText(row.delta_7d)\"></td>
                  <td class=\"px-4 py-4 font-semibold\" :class=\"deltaClass(row.delta_30d)\" x-text=\"deltaText(row.delta_30d)\"></td>
                  <td class=\"px-4 py-4 text-slate-700\" x-text=\"row.language || 'Unknown'\"></td>
                  <td class=\"px-4 py-4 text-slate-500\" x-text=\"row.updated_at || '-'\"></td>
                  <td class=\"max-w-md px-4 py-4 text-slate-500\" x-text=\"row.description || '-'\"></td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class=\"mt-6 rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-panel\">
      <h2 class=\"text-2xl font-black text-slate-950\">Current Stars</h2>
      <p class=\"mt-2 text-sm text-slate-600\">Top 15 repositories by current star count.</p>
      <div class=\"mt-4 overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white p-2\">
        {figure_html}
      </div>
    </section>

    <section class=\"mt-6 grid gap-6 xl:grid-cols-2\">
      <section x-show=\"showGrowth\" x-transition class=\"rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-panel\">
        <h2 class=\"text-2xl font-black text-slate-950\">Top Growing</h2>
        <p class=\"mt-2 text-sm text-slate-600\">Sorted by the best available window: 30d, then 7d, then previous snapshot.</p>
        <div class=\"mt-4 overflow-x-auto\">
          <table class=\"min-w-full divide-y divide-slate-200 text-sm\">
            <thead>
              <tr class=\"text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500\">
                <th class=\"px-0 py-3\">Repository</th>
                <th class=\"px-3 py-3\">Stars</th>
                <th class=\"px-3 py-3\">Today</th>
                <th class=\"px-3 py-3\">7d</th>
                <th class=\"px-3 py-3\">30d</th>
              </tr>
            </thead>
            <tbody class=\"divide-y divide-slate-100\">
              <template x-for=\"row in topGrowth\" :key=\"row.full_name\">
                <tr>
                  <td class=\"py-4\">
                    <a :href=\"row.html_url\" class=\"font-semibold text-slate-950 hover:text-orange-700\" x-text=\"row.full_name\"></a>
                  </td>
                  <td class=\"px-3 py-4 text-slate-700\" x-text=\"row.stargazers_count.toLocaleString()\"></td>
                  <td class=\"px-3 py-4 font-semibold\" :class=\"deltaClass(row.today_delta)\" x-text=\"deltaText(row.today_delta)\"></td>
                  <td class=\"px-3 py-4 font-semibold\" :class=\"deltaClass(row.delta_7d)\" x-text=\"deltaText(row.delta_7d)\"></td>
                  <td class=\"px-3 py-4 font-semibold\" :class=\"deltaClass(row.delta_30d)\" x-text=\"deltaText(row.delta_30d)\"></td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>

      <section x-show=\"showRecent\" x-transition class=\"rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-panel\">
        <h2 class=\"text-2xl font-black text-slate-950\">Recently Updated</h2>
        <p class=\"mt-2 text-sm text-slate-600\">Latest repositories by push or update timestamp in the current snapshot.</p>
        <div class=\"mt-4 overflow-x-auto\">
          <table class=\"min-w-full divide-y divide-slate-200 text-sm\">
            <thead>
              <tr class=\"text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500\">
                <th class=\"px-0 py-3\">Repository</th>
                <th class=\"px-3 py-3\">Stars</th>
                <th class=\"px-3 py-3\">Language</th>
                <th class=\"px-3 py-3\">Pushed</th>
              </tr>
            </thead>
            <tbody class=\"divide-y divide-slate-100\">
              <template x-for=\"row in recentUpdates\" :key=\"row.full_name\">
                <tr>
                  <td class=\"py-4\">
                    <a :href=\"row.html_url\" class=\"font-semibold text-slate-950 hover:text-cyan-700\" x-text=\"row.full_name\"></a>
                  </td>
                  <td class=\"px-3 py-4 text-slate-700\" x-text=\"row.stargazers_count.toLocaleString()\"></td>
                  <td class=\"px-3 py-4 text-slate-700\" x-text=\"row.language || 'Unknown'\"></td>
                  <td class=\"px-3 py-4 text-slate-500\" x-text=\"row.pushed_at || row.updated_at || '-'\"></td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  </main>
</body>
</html>
"""


def _sum_optional(rows: list[dict[str, Any]], key: str) -> int | None:
    values = [row[key] for row in rows if row[key] is not None]
    return sum(values) if values else None


def _format_delta(value: int) -> str:
    return f"{value:+,}"


def _format_optional_delta(value: int | None) -> str:
    return "n/a" if value is None else _format_delta(value)


def _format_best_delta(row: dict[str, Any]) -> str:
    best = row["delta_30d"]
    if best is None:
        best = row["delta_7d"]
    if best is None:
        best = row["today_delta"]
    return _format_optional_delta(best)


def _read_git_metadata() -> dict[str, str] | None:
    repo_root = Path(__file__).resolve().parent
    try:
        branch = _run_git_command(repo_root, "branch", "--show-current")
        commit = _run_git_command(repo_root, "rev-parse", "--short", "HEAD")
        committed_at = _run_git_command(repo_root, "show", "-s", "--format=%cI", "HEAD")
    except (OSError, RuntimeError, subprocess.CalledProcessError):
        return None

    if not branch or not commit or not committed_at:
        return None

    return {
        "branch": branch,
        "commit": commit,
        "committed_at": committed_at,
    }


def _run_git_command(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
