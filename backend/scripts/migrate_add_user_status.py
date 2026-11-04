"""Tambah kolom status akun ke tabel users dan tabel invitations (aman diulang).

WAJIB dijalankan di server SEBELUM deploy versi Creator Portal v2.1. Tanpa kolom
dan tabel ini, model User yang baru akan gagal saat query tabel users dan
endpoint undangan tidak bisa dipakai.

Kolom username ditambahkan belakangan. Kalau skrip ini sudah pernah dijalankan,
jalankan LAGI sebelum deploy versi yang memakai login username; tanpa kolom itu
semua query ke tabel users (termasuk login admin) gagal.

Jalankan dari folder backend:
    venv/bin/python scripts/migrate_add_user_status.py

Kolom baru:
    account_status  Pending | Active | Inactive (default Pending)
    created_at      ISO timestamp UTC saat daftar
    username        login selain email, unik (index ix_users_username);
                    NULL untuk akun lama

Tabel baru:
    invitations     undangan pendaftaran kreator (email, token, kedaluwarsa)

Di akhir, semua akun Admin di-set Active.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402
from database import SQLALCHEMY_DATABASE_URL, Base, engine  # noqa: E402
import models  # noqa: E402

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    sys.exit("DATABASE_URL belum menunjuk ke PostgreSQL. Batal.")

COLUMNS = [
    ("account_status", "VARCHAR NOT NULL DEFAULT 'Pending'"),
    ("created_at", "VARCHAR"),
    ("username", "VARCHAR"),
]

with engine.begin() as conn:
    for name, typ in COLUMNS:
        conn.execute(text(f'ALTER TABLE users ADD COLUMN IF NOT EXISTS "{name}" {typ}'))
        print(f"users.{name:20} ok")
    # Nama index sama dengan yang dibuat create_all untuk
    # Column(unique=True, index=True). NULL boleh lebih dari satu.
    conn.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")
    )
    print("index ix_users_username ok")
    Base.metadata.create_all(bind=conn, tables=[models.Invitation.__table__])
    print("tabel invitations     ok")
    updated = conn.execute(
        text("UPDATE users SET account_status='Active' WHERE role='Admin'")
    ).rowcount
    print(f"admin di-set Active: {updated}")

print("\nMigrasi selesai.")
