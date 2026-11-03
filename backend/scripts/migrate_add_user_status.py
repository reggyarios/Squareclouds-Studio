"""Tambah kolom status akun ke tabel users (aman diulang).

WAJIB dijalankan di server SEBELUM deploy versi Creator Portal v2. Tanpa kolom
ini, model User yang baru akan gagal saat query tabel users.

Jalankan dari folder backend:
    venv/bin/python scripts/migrate_add_user_status.py

Kolom baru:
    account_status  Pending | Active | Inactive (default Pending)
    created_at      ISO timestamp UTC saat daftar

Di akhir, semua akun Admin di-set Active.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402
from database import SQLALCHEMY_DATABASE_URL, engine  # noqa: E402

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    sys.exit("DATABASE_URL belum menunjuk ke PostgreSQL. Batal.")

COLUMNS = [
    ("account_status", "VARCHAR NOT NULL DEFAULT 'Pending'"),
    ("created_at", "VARCHAR"),
]

with engine.begin() as conn:
    for name, typ in COLUMNS:
        conn.execute(text(f'ALTER TABLE users ADD COLUMN IF NOT EXISTS "{name}" {typ}'))
        print(f"users.{name:20} ok")
    updated = conn.execute(
        text("UPDATE users SET account_status='Active' WHERE role='Admin'")
    ).rowcount
    print(f"admin di-set Active: {updated}")

print("\nMigrasi selesai.")
