"""Tambah kolom & tabel untuk pendapatan dan payout v2.2 (aman diulang).

WAJIB dijalankan di server SEBELUM deploy versi payout v2.2. Tanpa kolom baru
ini, model User dan DailySales yang baru gagal saat query (termasuk login).

Jalankan dari folder backend:
    venv/bin/python scripts/migrate_payouts.py
Setelah itu jalankan `venv/bin/python pathway_bot.py --full` supaya
gross_usd/net80_usd baris daily_sales lama ikut terisi.

Kolom baru:
    daily_sales.gross_usd   field `gross` per hari dari Pathway
    daily_sales.net80_usd   field `creator` per hari dari Pathway (80% gross)
    users.payout_method     paypal | bank | ewallet
    users.payout_details    JSON tujuan payout

Tabel baru:
    settings    pengaturan admin; di-seed paypal_fee_pct dan idr_rate
                kalau belum ada (nilai yang sudah ada tidak ditimpa)
    payouts     riwayat pembayaran ke kreator
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402
from database import SQLALCHEMY_DATABASE_URL, Base, engine  # noqa: E402
import models  # noqa: E402

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    sys.exit("DATABASE_URL belum menunjuk ke PostgreSQL. Batal.")

COLUMNS = [
    ("daily_sales", "gross_usd", "DOUBLE PRECISION NOT NULL DEFAULT 0"),
    ("daily_sales", "net80_usd", "DOUBLE PRECISION NOT NULL DEFAULT 0"),
    ("users", "payout_method", "VARCHAR"),
    ("users", "payout_details", "VARCHAR"),
]

now = datetime.now(timezone.utc).isoformat(timespec="seconds")

with engine.begin() as conn:
    for table, name, typ in COLUMNS:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{name}" {typ}'))
        print(f"{table}.{name:20} ok")
    Base.metadata.create_all(
        bind=conn,
        tables=[models.Setting.__table__, models.Payout.__table__],
    )
    print("tabel settings, payouts ok")
    for key, value in models.SETTING_DEFAULTS.items():
        inserted = conn.execute(
            text(
                'INSERT INTO settings ("key", "value", updated_at) '
                "VALUES (:key, :value, :now) ON CONFLICT (\"key\") DO NOTHING"
            ),
            {"key": key, "value": value, "now": now},
        ).rowcount
        print(f"settings.{key:20} {'di-seed ' + value if inserted else 'sudah ada'}")

print("\nMigrasi selesai.")
