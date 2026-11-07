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
                            Keduanya nullable tanpa default: NULL = belum
                            disinkron (earnings.py memakai fallback harga),
                            0 = Pathway memang melaporkan $0.
    users.payout_method     paypal | bank | ewallet
    users.payout_details    JSON tujuan payout

Versi awal skrip ini membuat kedua kolom daily_sales NOT NULL DEFAULT 0. Kalau
kolom seperti itu ditemukan, NOT NULL dan DEFAULT-nya dibuang, lalu baris yang
gross_usd DAN net80_usd-nya 0 di-set NULL (nilai default yang tidak bisa
dibedakan dari "belum disinkron"); `pathway_bot.py --full` mengisinya lagi
dengan angka Pathway, termasuk 0 yang asli.

Tabel baru:
    settings    pengaturan admin; di-seed paypal_fee_pct, idr_rate, dan
                company_address (alamat di slip payout PDF) kalau belum ada
                (nilai yang sudah ada tidak ditimpa)
    payouts     riwayat pembayaran ke kreator; kalau tabelnya sudah ada, kolom
                ini ikut ditambahkan:
                  notified_at    waktu email notifikasi terkirim
                  period_month   bulan yang dibayar (YYYY-MM); payout lama
                                 tetap NULL (tanpa periode)
                  drive_file_id  file ID slip PDF di Google Drive; NULL =
                                 belum tersimpan (bisa diupload ulang admin)
                plus unique index uq_payouts_user_period (user_id,
                period_month): satu payout per kreator per bulan
    payout_items
                rincian payout per konten (snapshot nama, unit, bagian, split),
                ON DELETE CASCADE dari payouts. Payout yang dicatat sebelum
                tabel ini ada tidak punya rincian.
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

AMOUNT_COLUMNS = ("gross_usd", "net80_usd")
COLUMNS = [
    ("daily_sales", "gross_usd", "DOUBLE PRECISION"),
    ("daily_sales", "net80_usd", "DOUBLE PRECISION"),
    ("users", "payout_method", "VARCHAR"),
    ("users", "payout_details", "VARCHAR"),
]

now = datetime.now(timezone.utc).isoformat(timespec="seconds")

with engine.begin() as conn:
    # Dicek sebelum ADD COLUMN: kolom NOT NULL hanya ada kalau versi awal
    # skrip ini pernah dijalankan.
    legacy_not_null = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'daily_sales' "
            "AND column_name = 'gross_usd' AND is_nullable = 'NO'"
        )
    ).first() is not None

    for table, name, typ in COLUMNS:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{name}" {typ}'))
        print(f"{table}.{name:20} ok")

    for name in AMOUNT_COLUMNS:
        conn.execute(
            text(
                f'ALTER TABLE daily_sales ALTER COLUMN "{name}" DROP NOT NULL, '
                f'ALTER COLUMN "{name}" DROP DEFAULT'
            )
        )
    print("daily_sales.gross_usd/net80_usd nullable tanpa default ok")
    if legacy_not_null:
        reset = conn.execute(
            text(
                "UPDATE daily_sales SET gross_usd = NULL, net80_usd = NULL "
                "WHERE gross_usd = 0 AND net80_usd = 0"
            )
        ).rowcount
        print(f"  {reset} baris bernilai default 0 di-set NULL (diisi lagi oleh pathway_bot.py --full)")
    Base.metadata.create_all(
        bind=conn,
        tables=[models.Setting.__table__, models.Payout.__table__, models.PayoutItem.__table__],
    )
    print("tabel settings, payouts, payout_items ok")
    # Setelah create_all: di DB baru tabel payouts baru ada di titik ini (sudah
    # dengan kolomnya); di DB lama kolom ini ditambahkan ke tabel yang ada.
    conn.execute(text('ALTER TABLE payouts ADD COLUMN IF NOT EXISTS "notified_at" VARCHAR'))
    print(f"{'payouts.notified_at':32} ok")
    conn.execute(text('ALTER TABLE payouts ADD COLUMN IF NOT EXISTS "period_month" VARCHAR'))
    print(f"{'payouts.period_month':32} ok")
    conn.execute(text('ALTER TABLE payouts ADD COLUMN IF NOT EXISTS "drive_file_id" VARCHAR'))
    print(f"{'payouts.drive_file_id':32} ok")
    # Nama sama dengan Index di models.Payout, jadi DB baru (create_all di
    # atas) dilewati di sini. NULL tidak bentrok: payout lama boleh banyak.
    conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_payouts_user_period "
            'ON payouts (user_id, "period_month")'
        )
    )
    print(f"{'payouts uq (user_id, period_month)':32} ok")
    for key, value in models.SETTING_DEFAULTS.items():
        inserted = conn.execute(
            text(
                'INSERT INTO settings ("key", "value", updated_at) '
                "VALUES (:key, :value, :now) ON CONFLICT (\"key\") DO NOTHING"
            ),
            {"key": key, "value": value, "now": now},
        ).rowcount
        shown = value.replace("\n", " / ")
        print(f"settings.{key:20} {'di-seed ' + shown if inserted else 'sudah ada'}")

print("\nMigrasi selesai.")
