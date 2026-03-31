import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from random import uniform

import httpx

from .models import PriceFixOffer

BASE_URL = "https://live.pks.fi"

MAX_ATTEMPTS = 10
INITIAL_WAIT = 10
MAX_WAIT = 300
BACKOFF_MULTIPLIER = 2

SEASON_TO_QUARTER = {
    "winter": 1,
    "spring": 2,
    "summer": 3,
    "autumn": 4,
}


@dataclass
class _PKSPeriod:
    id: int
    name: str
    start: datetime
    stop: datetime
    year: int
    quarter: int


def _create_session() -> httpx.Client:
    """Login via the public demo endpoint and return a client with session cookies."""
    client = httpx.Client(timeout=30, follow_redirects=True)
    resp = client.get(f"{BASE_URL}/demo")
    resp.raise_for_status()
    return client


def _fetch_periods(client: httpx.Client) -> list[_PKSPeriod]:
    resp = client.get(f"{BASE_URL}/Api/Periods/Available")
    resp.raise_for_status()
    periods = []
    for p in resp.json():
        if p["PeriodType"] != 1 or not p["IsAvailable"]:
            continue
        season = p.get("Season")
        if season not in SEASON_TO_QUARTER:
            continue
        start = datetime.fromisoformat(p["Start"])
        stop = datetime.fromisoformat(p["Stop"])
        quarter = SEASON_TO_QUARTER[season]
        # Q1 (winter) starts Dec 31 in UTC — use stop year
        year = stop.year if quarter == 1 else start.year
        periods.append(_PKSPeriod(
            id=p["Id"],
            name=p["Name"],
            start=start,
            stop=stop,
            year=year,
            quarter=quarter,
        ))
    return periods


def _fetch_current_vat(client: httpx.Client) -> float:
    resp = client.get(f"{BASE_URL}/Api/Periods/VatRates")
    resp.raise_for_status()
    now = datetime.now(timezone.utc)
    for rate in resp.json():
        start = datetime.fromisoformat(rate["Start"])
        stop = datetime.fromisoformat(rate["Stop"])
        if start <= now <= stop:
            return rate["Rate"]
    return resp.json()[-1]["Rate"]


def _fetch_price_graph(
    client: httpx.Client, period_id: int, use_vat: bool = False
) -> dict[str, float]:
    """Fetch daily price history for a period. Returns {date_str: price_c_kwh}."""
    vat_str = "true" if use_vat else "false"
    url = f"{BASE_URL}/Api/Prices/Period/Graph/{period_id}/24/{vat_str}/1/"
    resp = client.get(url)
    resp.raise_for_status()
    result: dict[str, float] = {}
    for ts_str, price in resp.json().items():
        dt = datetime.fromisoformat(ts_str)
        result[dt.strftime("%Y-%m-%d")] = price
    return result


def fetch_pks_offers() -> list[PriceFixOffer]:
    """Fetch current PKS prices. Returns one PriceFixOffer per quarterly period."""
    wait = INITIAL_WAIT

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            client = _create_session()
            try:
                return _do_fetch_offers(client)
            finally:
                client.close()

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise
            if attempt == MAX_ATTEMPTS:
                raise
            _log_retry(attempt, wait, f"HTTP {exc.response.status_code}")

        except httpx.TransportError as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            _log_retry(attempt, wait, str(exc) or type(exc).__name__)

        time.sleep(wait * uniform(0.8, 1.2))
        wait = min(wait * BACKOFF_MULTIPLIER, MAX_WAIT)

    return []  # unreachable


def _do_fetch_offers(client: httpx.Client) -> list[PriceFixOffer]:
    periods = _fetch_periods(client)
    vat_rate = _fetch_current_vat(client)
    vat_mult = 1 + vat_rate / 100
    now = datetime.now(timezone.utc)
    offers = []

    for period in periods:
        graph = _fetch_price_graph(client, period.id, use_vat=False)
        if not graph:
            continue
        sorted_dates = sorted(graph.keys())
        latest_date = sorted_dates[-1]
        price_vat0 = graph[latest_date]
        price_with_vat = round(price_vat0 * vat_mult, 6)
        change = 0.0
        if len(sorted_dates) >= 2:
            prev_vat0 = graph[sorted_dates[-2]]
            change = round((price_vat0 - prev_vat0) * vat_mult, 6)

        offers.append(PriceFixOffer(
            price_id=period.id,
            export_date=now,
            year=period.year,
            quarter=period.quarter,
            price_start_date=period.start,
            price_end_date=period.stop,
            price_vat0=price_vat0,
            vat=vat_rate,
            price_with_vat=price_with_vat,
            change=change,
            provider="pks",
        ))

    return offers


def fetch_pks_history() -> list[tuple]:
    """Fetch full PKS price history from graph API.
    Returns raw tuples suitable for db.store_pks_history()."""
    client = _create_session()
    try:
        periods = _fetch_periods(client)
        vat_rate = _fetch_current_vat(client)
        vat_mult = 1 + vat_rate / 100
        rows: list[tuple] = []

        for period in periods:
            graph = _fetch_price_graph(client, period.id, use_vat=False)
            sorted_dates = sorted(graph.keys())
            prev_price = None
            for d in sorted_dates:
                price_vat0 = graph[d]
                price_with_vat = round(price_vat0 * vat_mult, 6)
                change = round((price_vat0 - prev_price) * vat_mult, 6) if prev_price is not None else 0.0
                rows.append((
                    d,
                    period.id,
                    "pks",
                    period.year,
                    period.quarter,
                    period.start.isoformat(),
                    period.stop.isoformat(),
                    price_vat0,
                    vat_rate,
                    price_with_vat,
                    change,
                ))
                prev_price = price_vat0
        return rows
    finally:
        client.close()


def _log_retry(attempt: int, wait: float, reason: str) -> None:
    print(
        f"[pks retry {attempt}/{MAX_ATTEMPTS}] {reason} — retrying in ~{wait:.0f}s",
        file=sys.stderr,
    )
