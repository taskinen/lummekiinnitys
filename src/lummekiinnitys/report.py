import json
from collections import defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from .db import DB_PATH, load_all_offers

SERIES_COLORS = [
    "#96008f", "#e6194b", "#3cb44b", "#4363d8",
    "#f58231", "#911eb4", "#42d4f4", "#f032e6",
    "#bfef45", "#fabed4",
]


def generate_report(path: Path = DB_PATH) -> str:
    rows = load_all_offers(path)
    if not rows:
        return "<html><body><p>No data in database.</p></body></html>"

    providers = sorted({r.get("provider", "lumme") for r in rows})

    # Group by (provider, year, quarter)
    periods: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    for row in rows:
        provider = row.get("provider", "lumme")
        key = (provider, row["year"], row["quarter"])
        periods[key].append(row)

    sorted_periods = sorted(periods.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0]))

    # Per-provider date ranges
    provider_ranges: dict[str, tuple[str, str]] = {}
    for provider in providers:
        dates = [r["fetch_date"] for r in rows if r.get("provider", "lumme") == provider]
        provider_ranges[provider] = (min(dates), max(dates))

    # Latest rows per provider
    latest_rows = []
    for provider in providers:
        provider_rows = [r for r in rows if r.get("provider", "lumme") == provider]
        if provider_rows:
            prov_latest = max(r["fetch_date"] for r in provider_rows)
            latest_rows.extend(
                r for r in provider_rows if r["fetch_date"] == prov_latest
            )
    latest_rows.sort(key=lambda r: (r.get("provider", "lumme"), r["price_start_date"]))

    html_parts = [_html_header(provider_ranges, providers)]
    html_parts.append(_summary_table(latest_rows))

    chart_json = _chart_data(sorted_periods)
    html_parts.append('<h2>Price History</h2>')
    html_parts.append(_interactive_chart(chart_json))

    html_parts.append("</div></body></html>")
    return "\n".join(html_parts)


def _html_header(
    provider_ranges: dict[str, tuple[str, str]],
    providers: list[str],
) -> str:
    generated_iso = datetime.now(timezone.utc).isoformat()
    has_toggle = len(providers) > 1
    toggle_html = ""
    if has_toggle:
        toggle_html = """
<div class="toggle-group">
  <button class="toggle-btn active" onclick="filterProvider('all')">Both</button>
  <button class="toggle-btn" onclick="filterProvider('lumme')">Lumme</button>
  <button class="toggle-btn" onclick="filterProvider('pks')">PKS</button>
</div>"""

    provider_labels = {"lumme": "Lumme", "pks": "PKS"}
    subtitle_parts = []
    for p in providers:
        earliest, latest = provider_ranges[p]
        label = provider_labels.get(p, p)
        subtitle_parts.append(f"{label}: {earliest} \u2013 {latest}")
    subtitle = " &nbsp;|&nbsp; ".join(subtitle_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Electricity Price Fix Offers</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.min.css">
<script src="https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.iife.min.js"></script>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 900px;
    margin: 2rem auto;
    padding: 0 1rem;
    color: #1a1a1a;
    background: #fafafa;
  }}
  h1 {{ color: #96008f; margin-bottom: 0.2rem; }}
  .subtitle {{ color: #666; margin-bottom: 0.3rem; }}
  .report-age {{ color: #888; font-size: 0.9rem; margin-bottom: 1rem; }}
  .toggle-group {{
    display: flex; gap: 0; margin-bottom: 1.5rem;
  }}
  .toggle-btn {{
    padding: 0.4rem 1.2rem;
    border: 1px solid #96008f;
    background: white;
    color: #96008f;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
  }}
  .toggle-btn:first-child {{ border-radius: 4px 0 0 4px; }}
  .toggle-btn:last-child {{ border-radius: 0 4px 4px 0; }}
  .toggle-btn:not(:first-child) {{ border-left: none; }}
  .toggle-btn.active {{
    background: #96008f;
    color: white;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 2rem;
  }}
  th, td {{
    padding: 0.5rem 0.75rem;
    text-align: right;
    border-bottom: 1px solid #ddd;
  }}
  th {{ background: #96008f; color: white; }}
  td:first-child, th:first-child {{ text-align: left; }}
  td:nth-child(2), th:nth-child(2) {{ text-align: left; }}
  tr:hover td {{ background: #f0e6ef; }}
  tr.hidden {{ display: none; }}
  #chart {{ margin: 1rem 0 2rem; position: relative; }}
  #tooltip {{
    display: none;
    position: absolute;
    pointer-events: none;
    background: rgba(255,255,255,0.95);
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
    line-height: 1.5;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    z-index: 10;
    white-space: nowrap;
  }}
  #tooltip .tt-date {{ font-weight: bold; margin-bottom: 2px; }}
  #tooltip .tt-row {{ display: flex; align-items: center; gap: 6px; }}
  #tooltip .tt-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
</style>
</head>
<body>
<div>
<h1>Electricity Price Fix Offers</h1>
<p class="subtitle">{subtitle}</p>
<p class="report-age" id="report-age"></p>
{toggle_html}
<script>
(function() {{
  var generated = new Date("{generated_iso}");
  function update() {{
    var diff = Date.now() - generated.getTime();
    var mins = Math.floor(diff / 60000);
    var hours = Math.floor(mins / 60);
    var days = Math.floor(hours / 24);
    var text;
    if (mins < 1) text = "just now";
    else if (mins < 60) text = mins + " minute" + (mins !== 1 ? "s" : "") + " ago";
    else if (hours < 24) text = hours + " hour" + (hours !== 1 ? "s" : "") + " ago";
    else text = days + " day" + (days !== 1 ? "s" : "") + " ago";
    document.getElementById("report-age").textContent = "Report generated " + text;
  }}
  update();
  setInterval(update, 60000);
}})();
</script>
"""


def _summary_table(latest_rows: list[dict]) -> str:
    lines = [
        '<h2>Current Prices</h2>',
        '<table id="price-table">',
        '<tr><th>Period</th><th>Provider</th><th>Price (incl. VAT)</th></tr>',
    ]
    for r in latest_rows:
        start = r["price_start_date"][:10]
        end = r["price_end_date"][:10]
        provider = r.get("provider", "lumme")
        provider_label = provider.upper() if provider == "pks" else provider.capitalize()
        period = f"Q{r['quarter']}/{r['year']} ({start} \u2013 {end})"
        lines.append(
            f'<tr data-provider="{escape(provider)}">'
            f'<td>{escape(period)}</td>'
            f'<td>{escape(provider_label)}</td>'
            f'<td>{r["price_with_vat"]:.3f} c/kWh</td></tr>'
        )
    lines.append("</table>")
    return "\n".join(lines)


def _chart_data(
    sorted_periods: list[tuple[tuple[str, int, int], list[dict]]],
) -> str:
    all_dates = sorted({r["fetch_date"] for _, rows in sorted_periods for r in rows})
    date_index = {d: i for i, d in enumerate(all_dates)}

    timestamps = []
    for d in all_dates:
        dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        timestamps.append(int(dt.timestamp()))

    # Assign colors: same color per (year, quarter), dash for PKS
    period_keys = sorted({(yr, q) for (_, yr, q), _ in sorted_periods})
    color_map = {pk: SERIES_COLORS[i % len(SERIES_COLORS)] for i, pk in enumerate(period_keys)}

    series = []
    for (provider, year, quarter), period_rows in sorted_periods:
        label = f"Q{quarter}/{year} ({provider.upper() if provider == 'pks' else provider.capitalize()})"
        values: list[float | None] = [None] * len(all_dates)
        for r in period_rows:
            idx = date_index[r["fetch_date"]]
            values[idx] = round(r["price_with_vat"], 4)
        series.append({
            "label": label,
            "values": values,
            "provider": provider,
            "color": color_map[(year, quarter)],
            "dashed": provider == "pks",
        })

    return json.dumps({"timestamps": timestamps, "series": series})


def _interactive_chart(chart_data_json: str) -> str:
    return f"""<div id="chart"><div id="tooltip"></div></div>
<script>
(function() {{
  var raw = {chart_data_json};
  var tooltip = document.getElementById("tooltip");
  var currentFilter = "all";

  var data = [raw.timestamps];
  raw.series.forEach(function(s) {{ data.push(s.values); }});

  var seriesConfig = [{{}}];
  raw.series.forEach(function(s) {{
    seriesConfig.push({{
      label: s.label,
      stroke: s.color,
      width: 2,
      dash: s.dashed ? [6, 4] : undefined,
      points: {{ size: 0 }},
      provider: s.provider,
      value: function(u, v) {{ return v == null ? "--" : v.toFixed(3) + " c/kWh"; }}
    }});
  }});

  var el = document.getElementById("chart");

  var opts = {{
    width: Math.min(el.clientWidth, 880),
    height: 400,
    cursor: {{
      drag: {{ x: true, y: false }},
    }},
    plugins: [{{
      hooks: {{
        setCursor: [function(u) {{
          var idx = u.cursor.idx;
          var left = u.cursor.left;
          var top = u.cursor.top;
          if (idx == null || left < 0) {{
            tooltip.style.display = "none";
            return;
          }}
          var date = new Date(raw.timestamps[idx] * 1000);
          var dateStr = date.toISOString().slice(0, 10);
          var html = '<div class="tt-date">' + dateStr + '</div>';
          var hasAny = false;
          for (var i = 1; i < u.series.length; i++) {{
            if (!u.series[i].show) continue;
            var v = data[i][idx];
            if (v == null) continue;
            hasAny = true;
            var color = u.series[i]._stroke || u.series[i].stroke;
            if (typeof color === "function") color = color();
            html += '<div class="tt-row">'
              + '<span class="tt-dot" style="background:' + color + '"></span>'
              + '<span>' + u.series[i].label + ': ' + v.toFixed(3) + ' c/kWh</span>'
              + '</div>';
          }}
          if (!hasAny) {{
            tooltip.style.display = "none";
            return;
          }}
          tooltip.innerHTML = html;
          tooltip.style.display = "block";
          var tipW = tooltip.offsetWidth;
          var xPos = left + 15;
          if (xPos + tipW > el.clientWidth) xPos = left - tipW - 15;
          tooltip.style.left = xPos + "px";
          tooltip.style.top = (top + 15) + "px";
        }}]
      }}
    }}],
    scales: {{
      x: {{ time: true }},
      y: {{ range: function(u, min, max) {{ return [0, max]; }} }},
    }},
    axes: [
      {{
        stroke: "#666",
        grid: {{ stroke: "#e0e0e0" }},
      }},
      {{
        stroke: "#666",
        grid: {{ stroke: "#e0e0e0" }},
        label: "c/kWh (incl. VAT)",
        size: 60,
        values: function(u, vals) {{ return vals.map(function(v) {{ return v.toFixed(2); }}); }},
      }}
    ],
    series: seriesConfig,
  }};

  var chart = new uPlot(opts, data, el);

  el.addEventListener("dblclick", function() {{
    chart.setScale("x", {{
      min: raw.timestamps[0],
      max: raw.timestamps[raw.timestamps.length - 1]
    }});
  }});

  window.addEventListener("resize", function() {{
    chart.setSize({{
      width: Math.min(el.clientWidth, 880),
      height: 400
    }});
  }});

  // Provider toggle
  window.filterProvider = function(provider) {{
    currentFilter = provider;
    // Update buttons
    var btns = document.querySelectorAll(".toggle-btn");
    btns.forEach(function(btn) {{
      var target = btn.getAttribute("onclick").match(/'([^']+)'/)[1];
      btn.classList.toggle("active", target === provider);
    }});
    // Update table rows
    var trs = document.querySelectorAll("#price-table tr[data-provider]");
    trs.forEach(function(tr) {{
      var p = tr.getAttribute("data-provider");
      tr.classList.toggle("hidden", provider !== "all" && p !== provider);
    }});
    // Update chart series
    for (var i = 1; i < seriesConfig.length; i++) {{
      var show = provider === "all" || seriesConfig[i].provider === provider;
      chart.setSeries(i, {{ show: show }});
    }}
  }};
}})();
</script>"""
