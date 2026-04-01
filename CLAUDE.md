# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
This file should always be kept up to date with changes if needed.

## Project Overview

Python tool to fetch and track fixed electricity price offerings (hintakiinnitykset) from multiple providers. Currently supports **Lumme Energia** and **PKS (Pohjois-Karjalan Sähkö)**. Prices change daily and are stored for historical analysis.

## Commands

- **Show prices:** `uv run -m hintakiinnitys`
- **Store to DB:** `uv run -m hintakiinnitys store`
- **HTML report:** `uv run -m hintakiinnitys report > report.html`
- **Backfill PKS history:** `uv run -m hintakiinnitys backfill-pks`
- **Add dependency:** `uv add <package>`

## Project Structure

Uses `src` layout with `uv_build` backend:

```
src/hintakiinnitys/
  __main__.py   — CLI entry point
  client.py     — Lumme Energia API client (fetch_offers)
  pks_client.py — PKS API client (fetch_pks_offers, fetch_pks_history)
  db.py         — SQLite storage (store_offers, store_pks_history, load_all_offers, init_db)
  models.py     — dataclasses (PriceFixOffer)
  report.py     — HTML report generator with interactive charts and provider toggle
```

## APIs

### Lumme Energia

Open and unauthenticated:

- **Base URL:** `https://api-omalumme-prod.azure-api.net/FA-OmaLumme-Prod`
- `GET /v1/priceFixOffers` — quarterly fixed price offerings (c/kWh, VAT info, date range)

### PKS (Pohjois-Karjalan Sähkö)

Accessed via public demo session on old ASP.NET MVC site:

- **Base URL:** `https://live.pks.fi`
- `GET /demo` — creates demo session (sets auth cookies)
- `GET /Api/Periods/Available` — quarterly periods with metadata (Id, Name, Season, Start/Stop)
- `GET /Api/Prices/Period/Graph/{periodId}/24/{useVat}/{tubeType}/` — daily price history
- `GET /Api/Periods/VatRates` — VAT rate history

Season-to-quarter mapping: winter=Q1, spring=Q2, summer=Q3, autumn=Q4. Filter to `PeriodType==1` for quarterly periods.

Offerings and time periods are dynamic — never hardcode them.

## Conventions

- Python >=3.12, managed with `uv`
- `httpx` for HTTP requests
- Standard `dataclasses` for data models
- SQLite via Python's built-in `sqlite3` — DB file at project root (`prices.db`)
- One row per offer per day per provider — PK is `(fetch_date, price_id, provider)`
- `provider` column distinguishes data sources (`"lumme"` or `"pks"`)
- `prices.db` is tracked in git (committed by CI daily)

## CI/CD

GitHub Actions workflow (`.github/workflows/daily.yml`):
- Runs daily at 05:00 UTC (~8 AM Finnish time) + manual trigger
- Fetches prices from both providers, commits `prices.db`, generates report, deploys to GitHub Pages
- Requires GitHub Pages source set to "GitHub Actions" in repo settings
