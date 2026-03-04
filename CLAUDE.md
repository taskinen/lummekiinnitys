# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
This file should always be kept up to date with changes if needed.

## Project Overview

Python tool to fetch and track Lumme Energia's fixed electricity price offerings (hintakiinnitykset). Prices change daily and are stored for historical analysis.

## Commands

- **Show prices:** `uv run -m lummekiinnitys`
- **Store to DB:** `uv run -m lummekiinnitys store`
- **HTML report:** `uv run -m lummekiinnitys report > report.html`
- **Add dependency:** `uv add <package>`

## Project Structure

Uses `src` layout with `uv_build` backend:

```
src/lummekiinnitys/
  __main__.py   — CLI entry point
  client.py     — API client (fetch_offers)
  db.py         — SQLite storage (store_offers, load_all_offers, init_db)
  models.py     — dataclasses (PriceFixOffer)
  report.py     — HTML report generator with SVG charts
```

## API

Lumme Energia's API is open and unauthenticated:

- **Base URL:** `https://api-omalumme-prod.azure-api.net/FA-OmaLumme-Prod`
- `GET /v1/priceFixOffers` — quarterly fixed price offerings (c/kWh, VAT info, date range)

Offerings and time periods are dynamic — never hardcode them.

## Conventions

- Python >=3.12, managed with `uv`
- `httpx` for HTTP requests
- Standard `dataclasses` for data models
- SQLite via Python's built-in `sqlite3` — DB file at project root (`prices.db`)
- One row per offer per day — PK is `(fetch_date, price_id)`, uses `INSERT OR REPLACE`
- `prices.db` is tracked in git (committed by CI daily)

## CI/CD

GitHub Actions workflow (`.github/workflows/daily.yml`):
- Runs daily at 05:00 UTC (~8 AM Finnish time) + manual trigger
- Fetches prices, commits `prices.db`, generates report, deploys to GitHub Pages
- Requires GitHub Pages source set to "GitHub Actions" in repo settings
