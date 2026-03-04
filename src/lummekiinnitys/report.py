from collections import defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from .db import DB_PATH, load_all_offers


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
    html_parts.append('<h2>Price History by Period</h2>')

    for (year, quarter), period_rows in sorted_periods:
        start = period_rows[0]["price_start_date"][:10]
        end = period_rows[0]["price_end_date"][:10]
        title = f"Q{quarter}/{year} ({start} – {end})"
        html_parts.append(f"<h3>{escape(title)}</h3>")
        html_parts.append(_svg_chart(period_rows))

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
  h3 {{ color: #555; margin-top: 2rem; }}
  svg {{ display: block; margin: 0.5rem 0 1.5rem; }}
  .chart-line {{ fill: none; stroke: #96008f; stroke-width: 2; }}
  .chart-dot {{ fill: #96008f; }}
  .chart-grid {{ stroke: #e0e0e0; stroke-width: 1; }}
  .chart-axis {{ stroke: #999; stroke-width: 1; }}
  .chart-label {{ font-size: 11px; fill: #666; }}
  .chart-value {{ font-size: 10px; fill: #96008f; font-weight: bold; }}
  .toggle-wrap {{
    display: inline-flex;
    align-items: center;
    margin-left: 0.8rem;
    font-size: 0.85rem;
    vertical-align: middle;
  }}
  .toggle-label {{ color: #888; cursor: pointer; user-select: none; }}
  .toggle-label.active {{ color: #96008f; font-weight: bold; }}
  .toggle-track {{
    width: 40px;
    height: 22px;
    background: #96008f;
    border-radius: 11px;
    margin: 0 0.4rem;
    cursor: pointer;
    position: relative;
    transition: background 0.2s;
  }}
  .toggle-track::after {{
    content: "";
    position: absolute;
    top: 3px;
    left: 3px;
    width: 16px;
    height: 16px;
    background: white;
    border-radius: 50%;
    transition: transform 0.2s;
  }}
  .toggle-track.off::after {{ transform: translateX(18px); }}
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
        '<h2>Current Prices'
        ' <span class="toggle-wrap">'
        '<span class="toggle-label active" id="lbl-vat" onclick="toggleVat()">VAT</span>'
        '<span class="toggle-track" id="toggle-track" onclick="toggleVat()"></span>'
        '<span class="toggle-label" id="lbl-novat" onclick="toggleVat()">No VAT</span>'
        '</span></h2>',
        '<table id="price-table">',
        '<tr><th>Period</th><th id="price-header">Price (incl. VAT)</th></tr>',
    ]
    for r in latest_rows:
        start = r["price_start_date"][:10]
        end = r["price_end_date"][:10]
        period = f"Q{r['quarter']}/{r['year']} ({start} – {end})"
        lines.append(
            f'<tr><td>{escape(period)}</td>'
            f'<td class="price-cell" data-vat="{r["price_with_vat"]:.3f}" '
            f'data-vat0="{r["price_vat0"]:.3f}">{r["price_with_vat"]:.3f} c/kWh</td></tr>'
        )
    lines.append("</table>")
    lines.append("""<script>
var showingVat = true;
function toggleVat() {
  showingVat = !showingVat;
  var cells = document.querySelectorAll(".price-cell");
  var attr = showingVat ? "data-vat" : "data-vat0";
  for (var i = 0; i < cells.length; i++) {
    cells[i].textContent = cells[i].getAttribute(attr) + " c/kWh";
  }
  document.getElementById("price-header").textContent =
    showingVat ? "Price (incl. VAT)" : "Price (excl. VAT)";
  document.getElementById("toggle-track").classList.toggle("off", !showingVat);
  document.getElementById("lbl-vat").classList.toggle("active", showingVat);
  document.getElementById("lbl-novat").classList.toggle("active", !showingVat);
}
</script>""")
    return "\n".join(lines)


def _svg_chart(period_rows: list[dict]) -> str:
    # Collect data points: (fetch_date_str, price_with_vat)
    data = [(r["fetch_date"], r["price_with_vat"]) for r in period_rows]

    if len(data) == 0:
        return "<p>No data</p>"

    # Chart dimensions
    w, h = 700, 280
    pad_left, pad_right, pad_top, pad_bottom = 60, 20, 20, 50

    plot_w = w - pad_left - pad_right
    plot_h = h - pad_top - pad_bottom

    prices = [p for _, p in data]
    min_p = min(prices)
    max_p = max(prices)

    # Add some padding to y range
    y_margin = max((max_p - min_p) * 0.15, 0.5)
    y_min = min_p - y_margin
    y_max = max_p + y_margin

    def x_pos(i: int) -> float:
        if len(data) == 1:
            return pad_left + plot_w / 2
        return pad_left + (i / (len(data) - 1)) * plot_w

    def y_pos(price: float) -> float:
        if y_max == y_min:
            return pad_top + plot_h / 2
        return pad_top + (1 - (price - y_min) / (y_max - y_min)) * plot_h

    parts = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">']

    # Y-axis gridlines and labels
    n_yticks = 5
    for i in range(n_yticks + 1):
        val = y_min + (y_max - y_min) * i / n_yticks
        y = y_pos(val)
        parts.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{w - pad_right}" y2="{y:.1f}" class="chart-grid"/>')
        parts.append(f'<text x="{pad_left - 5}" y="{y + 4:.1f}" text-anchor="end" class="chart-label">{val:.2f}</text>')

    # Axes
    parts.append(f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{h - pad_bottom}" class="chart-axis"/>')
    parts.append(f'<line x1="{pad_left}" y1="{h - pad_bottom}" x2="{w - pad_right}" y2="{h - pad_bottom}" class="chart-axis"/>')

    # Y-axis label
    parts.append(
        f'<text x="15" y="{pad_top + plot_h / 2}" text-anchor="middle" '
        f'transform="rotate(-90, 15, {pad_top + plot_h / 2})" class="chart-label">c/kWh (incl. VAT)</text>'
    )

    # X-axis date labels — show a reasonable subset
    max_labels = 12
    step = max(1, len(data) // max_labels)
    for i in range(0, len(data), step):
        x = x_pos(i)
        label = data[i][0]  # fetch_date string
        parts.append(
            f'<text x="{x:.1f}" y="{h - pad_bottom + 18}" text-anchor="middle" class="chart-label">{escape(label)}</text>'
        )
    # Always show last label if not already shown
    if (len(data) - 1) % step != 0 and len(data) > 1:
        x = x_pos(len(data) - 1)
        label = data[-1][0]
        parts.append(
            f'<text x="{x:.1f}" y="{h - pad_bottom + 18}" text-anchor="middle" class="chart-label">{escape(label)}</text>'
        )

    # Line path
    if len(data) > 1:
        points = " ".join(f"{x_pos(i):.1f},{y_pos(p):.1f}" for i, (_, p) in enumerate(data))
        parts.append(f'<polyline points="{points}" class="chart-line"/>')

    # Dots and value labels
    for i, (d, p) in enumerate(data):
        x = x_pos(i)
        y = y_pos(p)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" class="chart-dot"/>')
        parts.append(f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" class="chart-value">{p:.3f}</text>')

    parts.append("</svg>")
    return "\n".join(parts)
