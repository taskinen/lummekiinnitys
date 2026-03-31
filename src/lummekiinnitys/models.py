from dataclasses import dataclass
from datetime import datetime


@dataclass
class PriceFixOffer:
    price_id: int
    export_date: datetime
    year: int
    quarter: int
    price_start_date: datetime
    price_end_date: datetime
    price_vat0: float
    vat: float
    price_with_vat: float
    change: float
    provider: str = "lumme"

    @classmethod
    def from_dict(cls, data: dict) -> "PriceFixOffer":
        return cls(
            price_id=data["Price_id"],
            export_date=datetime.fromisoformat(data["Export_date"]),
            year=data["Year"],
            quarter=data["Quarter"],
            price_start_date=datetime.fromisoformat(data["Price_start_date"]),
            price_end_date=datetime.fromisoformat(data["Price_end_date"]),
            price_vat0=data["priceVat0"],
            vat=data["vat"],
            price_with_vat=data["priceWithVat"],
            change=data["change"],
        )
