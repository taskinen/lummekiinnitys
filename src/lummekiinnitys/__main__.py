import sys

from .client import fetch_offers
from .db import store_offers


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else None

    if command is not None and command not in ("store", "report"):
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Usage: uv run -m lummekiinnitys [store|report]", file=sys.stderr)
        sys.exit(1)

    if command == "report":
        from .report import generate_report

        print(generate_report())
        return

    offers = fetch_offers()

    if command == "store":
        store_offers(offers)
        print("Stored to database.")
        print()

    offers.sort(key=lambda o: o.price_start_date)

    print(f"Lumme Energia - Fixed Price Offers (updated {offers[0].export_date:%Y-%m-%d})")
    print()

    print(f"{'Period':<25} {'excl. VAT':>10} {'incl. VAT':>10} {'VAT %':>7} {'Change':>8}")
    print("-" * 62)

    for offer in offers:
        period = f"Q{offer.quarter}/{offer.year} ({offer.price_start_date:%m/%d}–{offer.price_end_date:%m/%d})"
        print(
            f"{period:<25} {offer.price_vat0:>9.3f}c {offer.price_with_vat:>9.3f}c {offer.vat:>6.1f}% {offer.change:>7.3f}"
        )



if __name__ == "__main__":
    main()
