# Lummekiinnitys

Track [Lumme Energia](https://www.lumme-energia.fi/) fixed electricity price offerings (*hintakiinnitykset*) over time.

Prices are fetched daily from Lumme Energia's public API, stored in a SQLite database, and published as an interactive HTML report.

**[View the latest report](https://taskinen.github.io/lummekiinnitys/)**

## What it does

Lumme Energia offers quarterly fixed-price electricity contracts. The offered prices change daily based on market conditions. This tool:

- Fetches all currently available fixed price offerings from the API
- Stores one snapshot per day in a SQLite database
- Generates a self-contained HTML report with:
  - Summary table of current prices (with VAT toggle)
  - SVG line chart per period showing how the offered price has changed over time

## Usage

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Show current prices
uv run -m lummekiinnitys

# Fetch prices and store to database
uv run -m lummekiinnitys store

# Generate HTML report from stored data
uv run -m lummekiinnitys report > report.html
```

## Automation

A GitHub Actions workflow runs daily:

1. Fetches the latest prices and stores them in `prices.db`
2. Commits the updated database to the repository
3. Generates the HTML report and deploys it to GitHub Pages

The workflow can also be triggered manually from the Actions tab.

## Project structure

```
src/lummekiinnitys/
  __main__.py   CLI entry point
  client.py     API client
  db.py         SQLite storage
  models.py     Data models
  report.py     HTML report generator with SVG charts
```

## License

This project is not affiliated with Lumme Energia. Price data is sourced from their publicly accessible API.
