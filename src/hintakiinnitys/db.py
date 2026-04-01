import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from .models import PriceFixOffer

DB_PATH = Path(__file__).resolve().parents[2] / "prices.db"


def init_db(path: Path = DB_PATH) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_offers (
                fetch_date TEXT NOT NULL,
                price_id INTEGER NOT NULL,
                provider TEXT NOT NULL DEFAULT 'lumme',
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                price_start_date TEXT NOT NULL,
                price_end_date TEXT NOT NULL,
                price_vat0 REAL NOT NULL,
                vat REAL NOT NULL,
                price_with_vat REAL NOT NULL,
                change REAL NOT NULL,
                PRIMARY KEY (fetch_date, price_id, provider)
            )
        """)
        # Migrate: add provider column if missing
        cols = [row[1] for row in conn.execute("PRAGMA table_info(price_offers)")]
        if "provider" not in cols:
            conn.executescript("""
                ALTER TABLE price_offers RENAME TO _price_offers_old;
                CREATE TABLE price_offers (
                    fetch_date TEXT NOT NULL,
                    price_id INTEGER NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'lumme',
                    year INTEGER NOT NULL,
                    quarter INTEGER NOT NULL,
                    price_start_date TEXT NOT NULL,
                    price_end_date TEXT NOT NULL,
                    price_vat0 REAL NOT NULL,
                    vat REAL NOT NULL,
                    price_with_vat REAL NOT NULL,
                    change REAL NOT NULL,
                    PRIMARY KEY (fetch_date, price_id, provider)
                );
                INSERT INTO price_offers
                    (fetch_date, price_id, provider, year, quarter,
                     price_start_date, price_end_date, price_vat0, vat,
                     price_with_vat, change)
                SELECT fetch_date, price_id, 'lumme', year, quarter,
                       price_start_date, price_end_date, price_vat0, vat,
                       price_with_vat, change
                FROM _price_offers_old;
                DROP TABLE _price_offers_old;
            """)


def load_all_offers(path: Path = DB_PATH) -> list[dict[str, Any]]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM price_offers ORDER BY provider, price_start_date, fetch_date"
        ).fetchall()
        return [dict(row) for row in rows]


def store_offers(
    offers: list[PriceFixOffer],
    fetch_date: date | None = None,
    path: Path = DB_PATH,
) -> None:
    if fetch_date is None:
        fetch_date = date.today()
    init_db(path)
    with sqlite3.connect(path) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO price_offers
                (fetch_date, price_id, provider, year, quarter, price_start_date,
                 price_end_date, price_vat0, vat, price_with_vat, change)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    fetch_date.isoformat(),
                    o.price_id,
                    o.provider,
                    o.year,
                    o.quarter,
                    o.price_start_date.isoformat(),
                    o.price_end_date.isoformat(),
                    o.price_vat0,
                    o.vat,
                    o.price_with_vat,
                    o.change,
                )
                for o in offers
            ],
        )


def store_pks_history(
    rows: list[tuple],
    path: Path = DB_PATH,
) -> None:
    """Bulk-insert PKS historical price rows. Uses INSERT OR IGNORE to avoid
    overwriting data that was already stored via the daily fetch."""
    init_db(path)
    with sqlite3.connect(path) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO price_offers
                (fetch_date, price_id, provider, year, quarter, price_start_date,
                 price_end_date, price_vat0, vat, price_with_vat, change)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
