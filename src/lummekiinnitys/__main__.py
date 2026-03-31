import sys

from .client import fetch_offers
from .db import store_offers, store_pks_history
from .pks_client import fetch_pks_offers, fetch_pks_history


def _print_table(offers: list) -> None:
    print(f"{'Period':<25} {'excl. VAT':>10} {'incl. VAT':>10} {'VAT %':>7} {'Change':>8}")
    print("-" * 62)
    for offer in offers:
        period = f"Q{offer.quarter}/{offer.year} ({offer.price_start_date:%m/%d}\u2013{offer.price_end_date:%m/%d})"
        print(
            f"{period:<25} {offer.price_vat0:>9.3f}c {offer.price_with_vat:>9.3f}c {offer.vat:>6.1f}% {offer.change:>7.3f}"
        )


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else None

    if command is not None and command not in ("store", "report", "backfill-pks"):
        print(f"Unknown command: {command}", file=sys.stderr)
        print(
            "Usage: uv run -m lummekiinnitys [store|report|backfill-pks]",
            file=sys.stderr,
        )
        sys.exit(1)

    if command == "report":
        from .report import generate_report

        print(generate_report())
        return

    if command == "backfill-pks":
        rows = fetch_pks_history()
        store_pks_history(rows)
        print(f"Backfilled {len(rows)} PKS price entries.")
        return

    lumme_offers = fetch_offers()
    pks_offers = fetch_pks_offers()

    if command == "store":
        store_offers(lumme_offers)
        store_offers(pks_offers)
        print("Stored to database.")
        print()

    lumme_offers.sort(key=lambda o: o.price_start_date)
    print(f"Lumme Energia ({lumme_offers[0].export_date:%Y-%m-%d})")
    print()
    _print_table(lumme_offers)

    if pks_offers:
        pks_offers.sort(key=lambda o: o.price_start_date)
        print()
        print(f"PKS ({pks_offers[0].export_date:%Y-%m-%d})")
        print()
        _print_table(pks_offers)


if __name__ == "__main__":
    main()
