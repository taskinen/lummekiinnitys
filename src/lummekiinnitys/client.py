import httpx

from .models import PriceFixOffer

BASE_URL = "https://api-omalumme-prod.azure-api.net/FA-OmaLumme-Prod"


def fetch_offers() -> list[PriceFixOffer]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{BASE_URL}/v1/priceFixOffers")
        resp.raise_for_status()
        return [PriceFixOffer.from_dict(item) for item in resp.json()]
