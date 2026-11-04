"""Kosongkan data portal kreator supaya pathway_bot.py bisa mulai dari nol.

DIHAPUS : daily_sales, sales_transactions, earning_history, payouts,
          creator_splits, contents, dan semua user dengan role selain "Admin".
TETAP   : akun Admin, settings (fee PayPal & kurs), dan semua tabel CMS (cms_*).

Jalankan dari folder backend:
    venv/bin/python scripts/reset_portal_data.py
Skrip minta ketik RESET sebagai konfirmasi.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402
from database import SQLALCHEMY_DATABASE_URL, engine  # noqa: E402

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    sys.exit("DATABASE_URL belum menunjuk ke PostgreSQL. Batal.")

with engine.connect() as conn:
    counts = {
        t: conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        for t in ("daily_sales", "sales_transactions", "earning_history",
                  "payouts", "creator_splits", "contents")
    }
    counts["users (non-admin)"] = conn.execute(
        text("SELECT COUNT(*) FROM users WHERE role <> 'Admin'")
    ).scalar()
    admins = conn.execute(
        text("SELECT email FROM users WHERE role = 'Admin'")
    ).scalars().all()

print("Akan dihapus:")
for k, v in counts.items():
    print(f"  {k:22} {v:6} baris")
print(f"Admin yang DIPERTAHANKAN: {', '.join(admins) or '(tidak ada!)'}")

if not admins:
    sys.exit("Tidak ada akun Admin di tabel users. Batal, supaya tidak terkunci.")

if input("\nKetik RESET untuk melanjutkan: ").strip() != "RESET":
    sys.exit("Dibatalkan.")

with engine.begin() as conn:
    conn.execute(text("DELETE FROM daily_sales"))
    conn.execute(text("DELETE FROM sales_transactions"))
    conn.execute(text("DELETE FROM earning_history"))
    # Sebelum users: payouts.user_id (dan created_by) mengacu ke users.
    conn.execute(text("DELETE FROM payouts"))
    conn.execute(text("DELETE FROM creator_splits"))
    conn.execute(text("DELETE FROM contents"))
    conn.execute(text("DELETE FROM users WHERE role <> 'Admin'"))
    for t in ("daily_sales", "sales_transactions", "earning_history",
              "payouts", "creator_splits", "contents"):
        conn.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), 1, false)"
        ))

print("Selesai. Data portal (termasuk riwayat payout) kosong; admin, settings & CMS tetap utuh.")
