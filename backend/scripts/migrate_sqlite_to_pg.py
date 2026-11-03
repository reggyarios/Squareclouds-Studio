"""Salin data squareclouds.db (SQLite) -> PostgreSQL. Jalankan dari folder backend."""
import sqlite3
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402
from database import Base, SQLALCHEMY_DATABASE_URL, engine  # noqa: E402
import models  # noqa: E402,F401

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    sys.exit("DATABASE_URL di .env belum menunjuk ke PostgreSQL. Batal.")

src = sqlite3.connect(BACKEND / "squareclouds.db")
src.row_factory = sqlite3.Row
sqlite_tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}

Base.metadata.create_all(bind=engine)

with engine.begin() as conn:
    for table in Base.metadata.sorted_tables:
        name = table.name
        if name not in sqlite_tables:
            print(f"{name:25} (tidak ada di SQLite, dilewati)")
            continue
        if conn.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar():
            sys.exit(f"Tabel {name} di PostgreSQL sudah berisi data. Batal.")
        rows = src.execute(f'SELECT * FROM "{name}"').fetchall()
        if rows:
            cols = [c.name for c in table.columns if c.name in rows[0].keys()]
            conn.execute(table.insert(), [{c: r[c] for c in cols} for r in rows])
        if "id" in table.columns:
            conn.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM \"{name}\"), 0) + 1, false)"
            ))
        pg = conn.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar()
        status = "OK" if pg == len(rows) else "MISMATCH"
        print(f"{name:25} sqlite={len(rows):5}  postgres={pg:5}  {status}")
        if status != "OK":
            raise SystemExit("Jumlah baris tidak cocok, transaksi di-rollback.")

print("\nSelesai. Semua tabel tersalin.")
