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
            marker_color="#f97316",
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
    leader_desc = (top_repo.get("description") or "").strip()
    leader_tip_class = " tooltip tooltip-top cursor-help" if leader_desc else ""
    leader_tip_attr = f' data-tip="{html.escape(leader_desc, quote=True)}"' if leader_desc else ""
    mover_desc = (top_growth[0].get("description") if top_growth else "") or ""
    mover_desc = mover_desc.strip()
    mover_tip_class = " tooltip tooltip-top cursor-help" if mover_desc else ""
    mover_tip_attr = f' data-tip="{html.escape(mover_desc, quote=True)}"' if mover_desc else ""
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
  <script>
    (function() {{
      try {{
        var saved = localStorage.getItem('pulse-theme');
        var theme = saved === 'light' || saved === 'dark' ? saved : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
      }} catch (e) {{
        document.documentElement.setAttribute('data-theme', 'dark');
      }}
    }})();
  </script>
  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css\">
  <style>
    .description-wrapper {{ display: block !important; width: 100%; }}
  </style>
  <script src=\"https://cdn.tailwindcss.com\"></script>
  <script defer src=\"https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js\"></script>
  <script>

    function repoPulseReport(payload) {{
      return {{
        rows: payload.rows,
        topGrowth: payload.top_growth,
        recentUpdates: payload.recent_updates,
        search: \"\",
        language: \"all\",
        sortKey: \"delta_30d\",
        sortDir: \"desc\",
        showGrowth: true,
        showRecent: true,
        page: 1,
        pageSize: 20,
        isDark: document.documentElement.getAttribute('data-theme') !== 'light',
        sortableKeys: [\"stars\", \"today\", \"delta_7d\", \"delta_30d\", \"growth_pct\", \"updated_at\"],
        pageSizeOptions: [20, 50, 100],
        init() {{
          this.initFromUrl();
          this.setPage(this.page);
          this.$watch('search', () => {{
            this.page = 1;
            this.syncStateToUrl();
          }});
          this.$watch('language', () => {{
            this.page = 1;
            this.syncStateToUrl();
          }});
          this.$watch('pageSize', (next) => {{
            if (!this.pageSizeOptions.includes(next)) {{
              this.pageSize = 20;
              return;
            }}
            this.page = 1;
            this.syncStateToUrl();
          }});
          window.addEventListener('keydown', (e) => {{
            if (!e.ctrlKey && !e.metaKey) return;
            if (e.key === '1') {{ e.preventDefault(); this.showGrowth = !this.showGrowth; }}
            else if (e.key === '2') {{ e.preventDefault(); this.showRecent = !this.showRecent; }}
          }});
        }},
        initFromUrl() {{
          try {{
            const url = new URL(window.location.href);
            const key = url.searchParams.get('sort');
            const dir = url.searchParams.get('dir');
            if (key && this.sortableKeys.includes(key)) this.sortKey = key;
            if (dir === 'asc' || dir === 'desc') this.sortDir = dir;
            const page = parseInt(url.searchParams.get('page') || '1', 10);
            if (Number.isInteger(page) && page >= 1) this.page = page;
            const size = parseInt(url.searchParams.get('size') || '20', 10);
            if (this.pageSizeOptions.includes(size)) this.pageSize = size;
          }} catch (e) {{ /* no-op */ }}
        }},
        syncStateToUrl() {{
          try {{
            const url = new URL(window.location.href);
            url.searchParams.set('sort', this.sortKey);
            url.searchParams.set('dir', this.sortDir);
            url.searchParams.set('page', String(this.page));
            url.searchParams.set('size', String(this.pageSize));
            history.replaceState({{}}, '', url);
          }} catch (e) {{ /* no-op */ }}
        }},
        toggleSort(key) {{
          if (!this.sortableKeys.includes(key)) return;
          if (this.sortKey === key) {{
            this.sortDir = this.sortDir === 'desc' ? 'asc' : 'desc';
          }} else {{
            this.sortKey = key;
            this.sortDir = 'desc';
          }}
          this.syncStateToUrl();
        }},
        ariaSortFor(key) {{
          if (this.sortKey !== key) return 'none';
          return this.sortDir === 'asc' ? 'ascending' : 'descending';
        }},
        indicatorClass(key) {{
          if (this.sortKey !== key) return 'opacity-25';
          return this.sortDir === 'asc'
            ? 'text-primary opacity-100 rotate-180'
            : 'text-primary opacity-100';
        }},
        toggleTheme() {{
          this.isDark = !this.isDark;
          const next = this.isDark ? 'dark' : 'light';
          document.documentElement.setAttribute('data-theme', next);
          try {{ localStorage.setItem('pulse-theme', next); }} catch (e) {{}}
        }},
        formatDate(value) {{
          if (!value) return '';
          const s = String(value);
          const t = s.indexOf('T');
          return t === -1 ? s : s.slice(0, t);
        }},
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
        get totalPages() {{
          return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
        }},
        get firstIndex() {{
          if (this.filteredRows.length === 0) return 0;
          return (this.page - 1) * this.pageSize + 1;
        }},
        get lastIndex() {{
          if (this.filteredRows.length === 0) return 0;
          return Math.min(this.page * this.pageSize, this.filteredRows.length);
        }},
        get pagedRows() {{
          const total = this.totalPages;
          const page = Math.min(Math.max(1, this.page), total);
          return this.filteredRows.slice((page - 1) * this.pageSize, page * this.pageSize);
        }},
        setPage(next) {{
          const total = this.totalPages;
          const clamped = Math.min(Math.max(1, next), total);
          if (clamped !== this.page) {{
            this.page = clamped;
            this.syncStateToUrl();
          }}
        }},
        setPageSize(next) {{
          if (!this.pageSizeOptions.includes(next)) return;
          if (this.pageSize === next) return;
          this.pageSize = next;
          this.page = 1;
          this.syncStateToUrl();
        }},
        compareRows(left, right) {{
          const dir = this.sortDir === \"asc\" ? 1 : -1;
          const cmpNullable = (l, r) => {{
            if (l === null && r === null) return 0;
            if (l === null) return 1;
            if (r === null) return -1;
            return (l - r) * dir;
          }};
          let primary = 0;
          switch (this.sortKey) {{
            case \"stars\":
              primary = (left.stargazers_count - right.stargazers_count) * dir;
              break;
            case \"today\":
              primary = cmpNullable(left.today_delta, right.today_delta);
              break;
            case \"delta_7d\":
              primary = cmpNullable(left.delta_7d, right.delta_7d);
              break;
            case \"delta_30d\":
              primary = cmpNullable(left.delta_30d, right.delta_30d);
              break;
            case \"growth_pct\":
              primary = cmpNullable(this.relativeGrowth(left), this.relativeGrowth(right));
              break;
            case \"updated_at\":
              primary = (left.updated_at || \"\").localeCompare(right.updated_at || \"\") * dir;
              break;
          }}
          if (primary !== 0) return primary;
          if (this.sortKey !== \"today\") {{
            const l = left.today_delta ?? -Infinity;
            const r = right.today_delta ?? -Infinity;
            const todayCmp = r - l;
            if (todayCmp !== 0) return todayCmp;
          }}
          return left.full_name.localeCompare(right.full_name);
        }},
        deltaClass(value) {{
          if (value === null || value === undefined) return \"text-base-content/40\";
          if (value === 0) return \"text-base-content/50\";
          if (value > 0) return \"text-success\";
          return \"text-error\";
        }},
        deltaText(value) {{
          if (value === null || value === undefined) return \"n/a\";
          return `${{value >= 0 ? \"+\" : \"\"}}${{value.toLocaleString()}}`;
        }},
        relativeGrowth(row) {{
          if (row.delta_7d == null) return null;
          if (!row.stargazers_count || row.stargazers_count <= 0) return null;
          return row.delta_7d / row.stargazers_count;
        }},
        growthPctText(row) {{
          const g = this.relativeGrowth(row);
          if (g === null) return \"n/a\";
          const pct = g * 100;
          const sign = pct >= 0 ? \"+\" : \"\";
          return `${{sign}}${{pct.toFixed(2)}}%`;
        }},
        growthPctClass(row) {{
          const g = this.relativeGrowth(row);
          if (g === null) return \"text-base-content/40\";
          if (g > 0) return \"text-success\";
          if (g < 0) return \"text-error\";
          return \"text-base-content/50\";
        }},
        repoName(row) {{
          if (!row.full_name) return \"\";
          const idx = row.full_name.indexOf(\"\\/\");
          return idx === -1 ? row.full_name : row.full_name.slice(idx + 1);
        }},
        ownerName(row) {{
          if (!row.full_name) return \"\";
          const idx = row.full_name.indexOf(\"\\/\");
          return idx === -1 ? \"\" : row.full_name.slice(0, idx);
        }},
        descriptionNeedsTip(row) {{
          const d = (row.description || \"\").trim();
          if (!d) return false;
          return d.length > 50;
        }},
        description(row) {{
          let d = (row.description || \"\").trim();
          d = d.replace(/^:[a-z0-9_+\\-]+:\\s*/i, \"\");
          if (d.length > 1 && d.startsWith('\"') && d.endsWith('\"')) {{
            d = d.slice(1, -1).trim();
          }}
          return d;
        }},
      }};
    }}
  </script>
</head>
<body class=\"min-h-screen bg-base-200 text-base-content\">
  <script id=\"report-data\" type=\"application/json\">{payload}</script>
  <main
    x-data=\"repoPulseReport(JSON.parse(document.getElementById('report-data').textContent))\"
    class=\"mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8\"
  >
    <section class=\"relative rounded-xl bg-base-100 p-6 shadow-xl md:p-8\">
      <label
        class=\"swap swap-rotate btn btn-ghost btn-sm btn-circle absolute right-4 top-4\"
        :aria-label=\"isDark ? 'Switch to light theme' : 'Switch to dark theme'\"
        title=\"Toggle theme\"
      >
        <input type=\"checkbox\" :checked=\"isDark\" @change=\"toggleTheme\" />
        <svg class=\"swap-on h-4 w-4\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">
          <circle cx=\"12\" cy=\"12\" r=\"4\"/>
          <path d=\"M12 2v2\"/>
          <path d=\"M12 20v2\"/>
          <path d=\"m4.93 4.93 1.41 1.41\"/>
          <path d=\"m17.66 17.66 1.41 1.41\"/>
          <path d=\"M2 12h2\"/>
          <path d=\"M20 12h2\"/>
          <path d=\"m6.34 17.66-1.41 1.41\"/>
          <path d=\"m19.07 4.93-1.41 1.41\"/>
        </svg>
        <svg class=\"swap-off h-4 w-4\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">
          <path d=\"M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z\"/>
        </svg>
      </label>
      <div class=\"flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between\">
        <div class=\"max-w-3xl\">
          <span class=\"badge badge-primary\">Growth analytics</span>
          <h1 class=\"mt-4 text-4xl font-black tracking-tight sm:text-5xl\" title=\"{tooltip_title}\">Repo-Pulse Lite</h1>
          <p class=\"mt-3 max-w-2xl text-base text-base-content/70 sm:text-lg\">
            Snapshot at {snapshot_at}. The full dataset is embedded in this file, so filtering and sorting stay client-side.
          </p>
        </div>
        <div class=\"grid min-w-full gap-3 sm:grid-cols-2 lg:min-w-[22rem]\">
          <button
            type=\"button\"
            @click=\"showGrowth = !showGrowth\"
            :class=\"showGrowth ? 'btn btn-primary h-auto flex-col items-start py-3' : 'btn btn-outline btn-primary h-auto flex-col items-start py-3'\"
          >
            <span class=\"text-sm font-semibold\">Top Growing</span>
            <span class=\"flex items-center gap-1 text-xs opacity-70\">
              <span x-text=\"showGrowth ? 'Visible' : 'Hidden'\"></span>
              <kbd class=\"kbd kbd-xs\">Ctrl+1</kbd>
            </span>
          </button>
          <button
            type=\"button\"
            @click=\"showRecent = !showRecent\"
            :class=\"showRecent ? 'btn btn-info h-auto flex-col items-start py-3' : 'btn btn-outline btn-info h-auto flex-col items-start py-3'\"
          >
            <span class=\"text-sm font-semibold\">Recently Updated</span>
            <span class=\"flex items-center gap-1 text-xs opacity-70\">
              <span x-text=\"showRecent ? 'Visible' : 'Hidden'\"></span>
              <kbd class=\"kbd kbd-xs\">Ctrl+2</kbd>
            </span>
          </button>
        </div>
      </div>

      <div class=\"mt-8 stats stats-vertical w-full overflow-x-hidden rounded-xl bg-base-100 shadow lg:stats-horizontal\">
        <div class=\"stat\">
          <div class=\"stat-title\">Repos</div>
          <div class=\"stat-value\">{len(rows)}</div>
          <div class=\"stat-desc\">Starred repositories in the latest snapshot.</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-title\">Total Stars</div>
          <div class=\"stat-value text-primary\">{total_stars:,}</div>
          <div class=\"stat-desc\">Combined stars across the current portfolio.</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-title\">Average</div>
          <div class=\"stat-value\">{avg_stars:,}</div>
          <div class=\"stat-desc\">Average stars per repository.</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-title\">Leader</div>
          <div class=\"stat-value text-2xl{leader_tip_class}\"{leader_tip_attr}>{top_repo["full_name"]}</div>
          <div class=\"stat-desc\">{top_repo["stargazers_count"]:,} stars right now.</div>
        </div>
      </div>

      <div class=\"mt-4 stats stats-vertical w-full overflow-x-hidden rounded-xl bg-base-100 shadow lg:stats-horizontal\">
        <div class=\"stat\">
          <div class=\"stat-title\">Today</div>
          <div class=\"stat-value text-success\">{_format_delta(total_today)}</div>
          <div class=\"stat-desc\">Change versus the previous snapshot.</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-title\">7 Days</div>
          <div class=\"stat-value text-warning\">{_format_optional_delta(total_7d)}</div>
          <div class=\"stat-desc\">Aggregate weekly growth.</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-title\">30 Days</div>
          <div class=\"stat-value text-info\">{_format_optional_delta(total_30d)}</div>
          <div class=\"stat-desc\">Aggregate monthly growth.</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-title\">Fastest Mover</div>
          <div class=\"stat-value text-2xl{mover_tip_class}\"{mover_tip_attr}>{top_growth[0]["full_name"] if top_growth else "-"}</div>
          <div class=\"stat-desc\">{_format_best_delta(top_growth[0]) if top_growth else "n/a"} by the best available window.</div>
        </div>
      </div>
    </section>

    <section class=\"rounded-xl bg-base-100 p-6 shadow-xl\">
      <div class=\"flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between\">
        <div>
          <h2 class=\"text-2xl font-black\">Snapshot Explorer</h2>
          <p class=\"mt-2 text-sm text-base-content/70\">Client-side filters and sorting over the embedded SQLite export.</p>
        </div>
        <div class=\"grid gap-3 md:grid-cols-2\">
          <label class=\"form-control w-full\">
            <div class=\"label\"><span class=\"label-text text-xs font-semibold uppercase tracking-wider text-base-content/60\">Search</span></div>
            <input
              x-model=\"search\"
              type=\"search\"
              placeholder=\"repo or description\"
              class=\"input input-bordered w-full\"
            >
          </label>
          <label class=\"form-control w-full\">
            <div class=\"label\"><span class=\"label-text text-xs font-semibold uppercase tracking-wider text-base-content/60\">Language</span></div>
            <select x-model=\"language\" class=\"select select-bordered w-full\">
              <option value=\"all\">All languages</option>
              <template x-for=\"item in languages\" :key=\"item\">
                <option :value=\"item\" x-text=\"item\"></option>
              </template>
            </select>
          </label>
        </div>
      </div>

      <div class=\"mt-6 overflow-clip rounded-lg border border-base-300 bg-base-100\">
        <div class=\"flex flex-wrap items-center justify-between gap-3 border-b border-base-300 bg-base-200 px-4 py-2 text-sm text-base-content/70\">
          <div class=\"flex items-center gap-3\">
            <span x-show=\"filteredRows.length > 0\" x-text=\"`Showing ${{firstIndex}}\u2013${{lastIndex}} of ${{filteredRows.length}}`\"></span>
            <span x-show=\"filteredRows.length === 0\" class=\"italic\">No repos match the current filters.</span>
          </div>
          <div class=\"flex items-center gap-2\">
            <label class=\"flex items-center gap-2\">
              <span class=\"text-xs uppercase tracking-wider text-base-content/60\">Per page</span>
              <select class=\"select select-bordered select-xs\" @change=\"setPageSize(parseInt($event.target.value, 10))\">
                <template x-for=\"size in pageSizeOptions\" :key=\"size\">
                  <option :value=\"size\" :selected=\"pageSize === size\" x-text=\"size\"></option>
                </template>
              </select>
            </label>
            <div class=\"join\">
              <button type=\"button\" class=\"btn btn-xs join-item\" :disabled=\"page <= 1\" @click=\"setPage(page - 1)\">\u2039 Prev</button>
              <span class=\"btn btn-xs join-item no-animation pointer-events-none\" x-text=\"`Page ${{page}} of ${{totalPages}}`\"></span>
              <button type=\"button\" class=\"btn btn-xs join-item\" :disabled=\"page >= totalPages\" @click=\"setPage(page + 1)\">Next \u203a</button>
            </div>
          </div>
        </div>
        <div>
          <table class=\"table table-zebra\">
            <thead class=\"sticky top-0 z-10 bg-base-100 text-sm font-semibold text-base-content/80\">
              <tr>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71\"/><path d=\"M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71\"/></svg>
                    Repository
                  </span>
                </th>
                <th :aria-sort=\"ariaSortFor('stars')\">
                  <button
                    type=\"button\"
                    @click=\"toggleSort('stars')\"
                    class=\"inline-flex items-center gap-1.5 cursor-pointer select-none rounded hover:text-base-content focus:outline-none focus-visible:ring focus-visible:ring-primary/40\"
                  >
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polygon points=\"12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2\"/></svg>
                    Stars
                    <svg
                      class=\"h-3 w-3 transition-transform\"
                      :class=\"indicatorClass('stars')\"
                      xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"
                    ><polyline points=\"6 9 12 15 18 9\"/></svg>
                  </button>
                </th>
                <th :aria-sort=\"ariaSortFor('today')\">
                  <button
                    type=\"button\"
                    @click=\"toggleSort('today')\"
                    class=\"inline-flex items-center gap-1.5 cursor-pointer select-none rounded hover:text-base-content focus:outline-none focus-visible:ring focus-visible:ring-primary/40\"
                  >
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"22 7 13.5 15.5 8.5 10.5 2 17\"/><polyline points=\"16 7 22 7 22 13\"/></svg>
                    Today
                    <svg
                      class=\"h-3 w-3 transition-transform\"
                      :class=\"indicatorClass('today')\"
                      xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"
                    ><polyline points=\"6 9 12 15 18 9\"/></svg>
                  </button>
                </th>
                <th :aria-sort=\"ariaSortFor('delta_7d')\">
                  <button
                    type=\"button\"
                    @click=\"toggleSort('delta_7d')\"
                    class=\"inline-flex items-center gap-1.5 cursor-pointer select-none rounded hover:text-base-content focus:outline-none focus-visible:ring focus-visible:ring-primary/40\"
                  >
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"22 7 13.5 15.5 8.5 10.5 2 17\"/><polyline points=\"16 7 22 7 22 13\"/></svg>
                    7d
                    <svg
                      class=\"h-3 w-3 transition-transform\"
                      :class=\"indicatorClass('delta_7d')\"
                      xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"
                    ><polyline points=\"6 9 12 15 18 9\"/></svg>
                  </button>
                </th>
                <th :aria-sort=\"ariaSortFor('delta_30d')\">
                  <button
                    type=\"button\"
                    @click=\"toggleSort('delta_30d')\"
                    class=\"inline-flex items-center gap-1.5 cursor-pointer select-none rounded hover:text-base-content focus:outline-none focus-visible:ring focus-visible:ring-primary/40\"
                  >
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"22 7 13.5 15.5 8.5 10.5 2 17\"/><polyline points=\"16 7 22 7 22 13\"/></svg>
                    30d
                    <svg
                      class=\"h-3 w-3 transition-transform\"
                      :class=\"indicatorClass('delta_30d')\"
                      xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"
                    ><polyline points=\"6 9 12 15 18 9\"/></svg>
                  </button>
                </th>
                <th :aria-sort=\"ariaSortFor('growth_pct')\">
                  <button
                    type=\"button\"
                    @click=\"toggleSort('growth_pct')\"
                    class=\"inline-flex items-center gap-1.5 cursor-pointer select-none rounded hover:text-base-content focus:outline-none focus-visible:ring focus-visible:ring-primary/40\"
                    title=\"Weekly star growth: delta_7d / stargazers_count\"
                  >
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><line x1=\"12\" y1=\"20\" x2=\"12\" y2=\"10\"/><line x1=\"18\" y1=\"20\" x2=\"18\" y2=\"4\"/><line x1=\"6\" y1=\"20\" x2=\"6\" y2=\"16\"/></svg>
                    Growth %
                    <svg
                      class=\"h-3 w-3 transition-transform\"
                      :class=\"indicatorClass('growth_pct')\"
                      xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"
                    ><polyline points=\"6 9 12 15 18 9\"/></svg>
                  </button>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"16 18 22 12 16 6\"/><polyline points=\"8 6 2 12 8 18\"/></svg>
                    Language
                  </span>
                </th>
                <th :aria-sort=\"ariaSortFor('updated_at')\">
                  <button
                    type=\"button\"
                    @click=\"toggleSort('updated_at')\"
                    class=\"inline-flex items-center gap-1.5 cursor-pointer select-none rounded hover:text-base-content focus:outline-none focus-visible:ring focus-visible:ring-primary/40\"
                  >
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><rect x=\"3\" y=\"4\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"/><line x1=\"16\" y1=\"2\" x2=\"16\" y2=\"6\"/><line x1=\"8\" y1=\"2\" x2=\"8\" y2=\"6\"/><line x1=\"3\" y1=\"10\" x2=\"21\" y2=\"10\"/></svg>
                    Updated
                    <svg
                      class=\"h-3 w-3 transition-transform\"
                      :class=\"indicatorClass('updated_at')\"
                      xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"
                    ><polyline points=\"6 9 12 15 18 9\"/></svg>
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              <template x-for=\"row in pagedRows\" :key=\"row.repo_id\">
                <tr class=\"hover:bg-base-200/40\">
                  <td>
                    <a :href=\"row.html_url\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link link-primary font-semibold leading-tight block\" x-text=\"repoName(row)\"></a>
                    <div class=\"text-xs text-base-content/50 leading-tight\" x-text=\"ownerName(row)\"></div>
                    <div class=\"description-wrapper\"
                         x-show=\"description(row)\"
                         :class=\"descriptionNeedsTip(row) ? 'tooltip tooltip-right cursor-help' : ''\"
                         :data-tip=\"descriptionNeedsTip(row) ? description(row) : ''\">
                      <p class=\"line-clamp-1 text-xs text-base-content/60 leading-tight\" x-text=\"description(row)\"></p>
                    </div>
                  </td>
                  <td x-text=\"row.stargazers_count.toLocaleString()\"></td>
                  <td class=\"font-semibold\" :class=\"deltaClass(row.today_delta)\" x-text=\"deltaText(row.today_delta)\"></td>
                  <td class=\"font-semibold\" :class=\"deltaClass(row.delta_7d)\" x-text=\"deltaText(row.delta_7d)\"></td>
                  <td class=\"font-semibold\" :class=\"deltaClass(row.delta_30d)\" x-text=\"deltaText(row.delta_30d)\"></td>
                  <td class=\"font-semibold\" :class=\"growthPctClass(row)\" x-text=\"growthPctText(row)\"></td>
                  <td x-text=\"row.language || 'Unknown'\"></td>
                  <td class=\"text-base-content/60\" x-text=\"formatDate(row.updated_at) || '-'\"></td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <div class=\"flex flex-wrap items-center justify-between gap-3 border-t border-base-300 bg-base-200 px-4 py-2 text-sm text-base-content/70\">
          <span x-text=\"`Page ${{page}} of ${{totalPages}}`\"></span>
          <div class=\"join\">
            <button type=\"button\" class=\"btn btn-xs join-item\" :disabled=\"page <= 1\" @click=\"setPage(page - 1)\">\u2039 Prev</button>
            <button type=\"button\" class=\"btn btn-xs join-item\" :disabled=\"page >= totalPages\" @click=\"setPage(page + 1)\">Next \u203a</button>
          </div>
        </div>
      </div>
    </section>

    <section class=\"rounded-xl bg-base-100 p-6 shadow-xl\">
      <h2 class=\"text-2xl font-black\">Current Stars</h2>
      <p class=\"mt-2 text-sm text-base-content/70\">Top 15 repositories by current star count.</p>
      <div class=\"mt-4 overflow-hidden rounded-lg border border-base-300 bg-base-100 p-2\">
        {figure_html}
      </div>
    </section>

    <section class=\"grid gap-6 xl:grid-cols-2\">
      <section x-show=\"showGrowth\" x-transition class=\"rounded-xl bg-base-100 p-6 shadow-xl\">
        <h2 class=\"text-2xl font-black\">Top Growing</h2>
        <p class=\"mt-2 text-sm text-base-content/70\">Sorted by the best available window: 30d, then 7d, then previous snapshot.</p>
        <div class=\"mt-4 overflow-x-auto\">
          <table class=\"table table-zebra\">
            <thead class=\"sticky top-0 z-10 bg-base-100 text-sm font-semibold text-base-content/80\">
              <tr>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71\"/><path d=\"M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71\"/></svg>
                    Repository
                  </span>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polygon points=\"12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2\"/></svg>
                    Stars
                  </span>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"22 7 13.5 15.5 8.5 10.5 2 17\"/><polyline points=\"16 7 22 7 22 13\"/></svg>
                    Today
                  </span>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"22 7 13.5 15.5 8.5 10.5 2 17\"/><polyline points=\"16 7 22 7 22 13\"/></svg>
                    7d
                  </span>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"22 7 13.5 15.5 8.5 10.5 2 17\"/><polyline points=\"16 7 22 7 22 13\"/></svg>
                    30d
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              <template x-for=\"row in topGrowth\" :key=\"row.full_name\">
                <tr class=\"hover:bg-base-200/40\">
                  <td>
                    <a :href=\"row.html_url\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link link-primary font-semibold\" x-text=\"row.full_name\"></a>
                  </td>
                  <td x-text=\"row.stargazers_count.toLocaleString()\"></td>
                  <td class=\"font-semibold\" :class=\"deltaClass(row.today_delta)\" x-text=\"deltaText(row.today_delta)\"></td>
                  <td class=\"font-semibold\" :class=\"deltaClass(row.delta_7d)\" x-text=\"deltaText(row.delta_7d)\"></td>
                  <td class=\"font-semibold\" :class=\"deltaClass(row.delta_30d)\" x-text=\"deltaText(row.delta_30d)\"></td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>

      <section x-show=\"showRecent\" x-transition class=\"rounded-xl bg-base-100 p-6 shadow-xl\">
        <h2 class=\"text-2xl font-black\">Recently Updated</h2>
        <p class=\"mt-2 text-sm text-base-content/70\">Latest repositories by push or update timestamp in the current snapshot.</p>
        <div class=\"mt-4 overflow-x-auto\">
          <table class=\"table table-zebra\">
            <thead class=\"sticky top-0 z-10 bg-base-100 text-sm font-semibold text-base-content/80\">
              <tr>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71\"/><path d=\"M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71\"/></svg>
                    Repository
                  </span>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polygon points=\"12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2\"/></svg>
                    Stars
                  </span>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><polyline points=\"16 18 22 12 16 6\"/><polyline points=\"8 6 2 12 8 18\"/></svg>
                    Language
                  </span>
                </th>
                <th>
                  <span class=\"inline-flex items-center gap-1.5\">
                    <svg class=\"h-3.5 w-3.5 opacity-60\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><rect x=\"3\" y=\"4\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"/><line x1=\"16\" y1=\"2\" x2=\"16\" y2=\"6\"/><line x1=\"8\" y1=\"2\" x2=\"8\" y2=\"6\"/><line x1=\"3\" y1=\"10\" x2=\"21\" y2=\"10\"/></svg>
                    Pushed
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              <template x-for=\"row in recentUpdates\" :key=\"row.full_name\">
                <tr class=\"hover:bg-base-200/40\">
                  <td>
                    <a :href=\"row.html_url\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link link-info font-semibold\" x-text=\"row.full_name\"></a>
                  </td>
                  <td x-text=\"row.stargazers_count.toLocaleString()\"></td>
                  <td x-text=\"row.language || 'Unknown'\"></td>
                  <td class=\"text-base-content/60\" x-text=\"formatDate(row.pushed_at) || formatDate(row.updated_at) || '-'\"></td>
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
