# Hintakiinnitys

Track fixed electricity price offerings (*hintakiinnitykset*) from Finnish providers over time. Currently supports [Lumme Energia](https://www.lumme-energia.fi/) and [PKS (Pohjois-Karjalan Sähkö)](https://www.pks.fi/).

Prices are fetched daily from each provider's public API, stored in a SQLite database, and published as an interactive HTML report.

**[View the latest report](https://taskinen.github.io/hintakiinnitys/)**

## What it does

Finnish electricity providers offer quarterly fixed-price contracts whose prices change daily based on market conditions. This tool:

- Fetches all currently available fixed price offerings from Lumme Energia and PKS
- Stores one snapshot per offer per day per provider in a SQLite database
- Generates a self-contained HTML report with:
  - Summary table of current prices from all providers
  - Interactive line chart showing how offered prices have changed over time
  - Provider toggle to filter by Lumme, PKS, or both

## Usage

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Show current prices from all providers
uv run -m hintakiinnitys

# Fetch prices and store to database
uv run -m hintakiinnitys store

# Generate HTML report from stored data
uv run -m hintakiinnitys report > report.html

# Backfill PKS historical prices
uv run -m hintakiinnitys backfill-pks
```

## Automation

A GitHub Actions workflow runs daily:

1. Fetches the latest prices from both providers and stores them in `prices.db`
2. Commits the updated database to the repository
3. Generates the HTML report and deploys it to GitHub Pages

The workflow can also be triggered manually from the Actions tab.

## Project structure

```
src/hintakiinnitys/
  __main__.py   CLI entry point
  client.py     Lumme Energia API client
  pks_client.py PKS API client
  db.py         SQLite storage
  models.py     Data models
  report.py     HTML report generator with interactive charts
```

## Disclaimer

Use of this software is at your own risk. Nobody assumes liability for any consequences. If this program accidentally cuts your house's electricity, consider it a stroke of luck that it didn't affect everyone else's electricity as well.

This project is not affiliated with Lumme Energia or PKS. Price data is sourced from their publicly accessible APIs.
