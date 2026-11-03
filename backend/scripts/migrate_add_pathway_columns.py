"""Tambah kolom Pathway ke tabel contents (aman diulang).

Jalankan dari folder backend:
    venv/bin/python scripts/migrate_add_pathway_columns.py
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
    ("pathway_product_id", "VARCHAR"),
    ("pathway_offer_id", "VARCHAR"),
    ("pathway_status", "VARCHAR"),
    ("pack_type", "VARCHAR"),
    ("world_type", "VARCHAR"),
    ("tier", "INTEGER"),
    ("release_date", "VARCHAR"),
    ("last_synced_at", "VARCHAR"),
]

with engine.begin() as conn:
    for name, typ in COLUMNS:
        conn.execute(text(f'ALTER TABLE contents ADD COLUMN IF NOT EXISTS "{name}" {typ}'))
        print(f"contents.{name:20} ok")
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_contents_pathway_product_id "
        "ON contents (pathway_product_id)"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_contents_pathway_offer_id "
        "ON contents (pathway_offer_id)"
    ))
    print("index ok")

print("\nMigrasi selesai.")
