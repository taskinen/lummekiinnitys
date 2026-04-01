import sys
import time
from random import uniform

import httpx

from .models import PriceFixOffer

BASE_URL = "https://api-omalumme-prod.azure-api.net/FA-OmaLumme-Prod"

MAX_ATTEMPTS = 10
INITIAL_WAIT = 10
MAX_WAIT = 300
BACKOFF_MULTIPLIER = 2


def fetch_offers() -> list[PriceFixOffer]:
    wait = INITIAL_WAIT

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(f"{BASE_URL}/v1/priceFixOffers")
                resp.raise_for_status()
                return [PriceFixOffer.from_dict(item) for item in resp.json()]

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


def _log_retry(attempt: int, wait: float, reason: str) -> None:
    print(
        f"[retry {attempt}/{MAX_ATTEMPTS}] {reason} — retrying in ~{wait:.0f}s",
        file=sys.stderr,
    )
