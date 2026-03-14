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

    # Group by period (year, quarter)
    periods: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in rows:
        key = (row["year"], row["quarter"])
        periods[key].append(row)

    # Sort periods by start date
    sorted_periods = sorted(periods.items(), key=lambda kv: kv[1][0]["price_start_date"])

    # Date range for header
    all_dates = [row["fetch_date"] for row in rows]
    earliest_date = min(all_dates)
    latest_date = max(all_dates)
    latest_rows = [r for r in rows if r["fetch_date"] == latest_date]
    latest_rows.sort(key=lambda r: r["price_start_date"])

    html_parts = [_html_header(earliest_date, latest_date)]
    html_parts.append(_summary_table(latest_rows))

    chart_json = _chart_data(sorted_periods)
    html_parts.append('<h2>Price History</h2>')
    html_parts.append(_interactive_chart(chart_json))

    html_parts.append("</div></body></html>")
    return "\n".join(html_parts)


def _html_header(earliest_date: str, latest_date: str) -> str:
    generated_iso = datetime.now(timezone.utc).isoformat()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lumme Energia – Fixed Price Report</title>
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
  .report-age {{ color: #888; font-size: 0.9rem; margin-bottom: 2rem; }}
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
  tr:hover td {{ background: #f0e6ef; }}
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
<h1>Lumme Energia – Fixed Price Offers</h1>
<p class="subtitle">Data from {earliest_date} to {latest_date}</p>
<p class="report-age" id="report-age"></p>
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
        '<tr><th>Period</th><th>Price (incl. VAT)</th></tr>',
    ]
    for r in latest_rows:
        start = r["price_start_date"][:10]
        end = r["price_end_date"][:10]
        period = f"Q{r['quarter']}/{r['year']} ({start} – {end})"
        lines.append(
            f'<tr><td>{escape(period)}</td>'
            f'<td>{r["price_with_vat"]:.3f} c/kWh</td></tr>'
        )
    lines.append("</table>")
    return "\n".join(lines)


def _chart_data(sorted_periods: list[tuple[tuple[int, int], list[dict]]]) -> str:
    all_dates = sorted({r["fetch_date"] for _, rows in sorted_periods for r in rows})
    date_index = {d: i for i, d in enumerate(all_dates)}

    timestamps = []
    for d in all_dates:
        dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        timestamps.append(int(dt.timestamp()))

    series = []
    for (year, quarter), period_rows in sorted_periods:
        label = f"Q{quarter}/{year}"
        values: list[float | None] = [None] * len(all_dates)
        for r in period_rows:
            idx = date_index[r["fetch_date"]]
            values[idx] = round(r["price_with_vat"], 4)
        series.append({"label": label, "values": values})

    return json.dumps({"timestamps": timestamps, "series": series})


def _interactive_chart(chart_data_json: str) -> str:
    colors_js = json.dumps(SERIES_COLORS)
    return f"""<div id="chart"><div id="tooltip"></div></div>
<script>
(function() {{
  var COLORS = {colors_js};
  var raw = {chart_data_json};
  var tooltip = document.getElementById("tooltip");

  var data = [raw.timestamps];
  raw.series.forEach(function(s) {{ data.push(s.values); }});

  var seriesConfig = [{{}}];
  raw.series.forEach(function(s, i) {{
    seriesConfig.push({{
      label: s.label,
      stroke: COLORS[i % COLORS.length],
      width: 2,
      points: {{ size: 5 }},
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
            html += '<div class="tt-row">'
              + '<span class="tt-dot" style="background:' + u.series[i].stroke() + '"></span>'
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
}})();
</script>"""
