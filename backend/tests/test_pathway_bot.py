"""pathway_bot.upsert: gross/net80 per hari dari Pathway ikut tersimpan."""
import models
import pathway_bot
from database import SessionLocal

PID = "prod-1"
CATALOG = [{"productID": PID, "contentName": "Royal Mansion"}]


def day(date, units, gross, creator):
    return {"date": date, "units": units, "gross": gross, "creator": creator}


def sales_rows():
    with SessionLocal() as db:
        return {
            s.date: (s.quantity, s.gross_usd, s.net80_usd)
            for s in db.query(models.DailySales)
        }


def test_upsert_stores_and_updates_gross_and_net80(client, capsys):
    days = [day("2026-10-01", 4, 3.0, 2.4), day("2026-10-02", 2, 1.5, 1.2), day("2026-10-03", 0, 0, 0)]
    pathway_bot.upsert([], CATALOG, {PID: days}, dry_run=False)
    assert sales_rows() == {"2026-10-01": (4, 3.0, 2.4), "2026-10-02": (2, 1.5, 1.2)}
    assert "daily_sales: +2 baru, 0 diperbarui" in capsys.readouterr().out

    # Unit sama, hanya nilai uang yang berubah -> tetap dihitung diperbarui.
    # Selisih <= 0.001 dianggap tidak berubah.
    days = [day("2026-10-01", 4, 3.75, 3.0), day("2026-10-02", 2, 1.5004, 1.2), day("2026-10-03", 0, 0, 0)]
    pathway_bot.upsert([], CATALOG, {PID: days}, dry_run=False)
    assert sales_rows() == {"2026-10-01": (4, 3.75, 3.0), "2026-10-02": (2, 1.5, 1.2)}
    assert "daily_sales: +0 baru, 1 diperbarui" in capsys.readouterr().out

    # Baris lama (sebelum kolom baru diisi) ikut terisi saat sinkron ulang.
    with SessionLocal() as db:
        row = db.query(models.DailySales).filter(models.DailySales.date == "2026-10-02").one()
        row.gross_usd = row.net80_usd = 0
        db.commit()
    pathway_bot.upsert([], CATALOG, {PID: days}, dry_run=False)
    assert sales_rows()["2026-10-02"] == (2, 1.5004, 1.2)
    assert "daily_sales: +0 baru, 1 diperbarui" in capsys.readouterr().out
