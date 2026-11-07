"""Pendapatan kreator, payout, dan pengaturan (docs/payout-v2.2.md).

Checklist §6 spek:
- rumus 100 → 80 → 76 → 22,8 dan saldo setelah payout:
  test_money_chain_gross_net80_net_share, test_outstanding_decreases_after_payout
- POST /payouts melebihi saldo / tanpa metode / non-admin:
  test_create_payout_rejections, test_settings_and_payout_endpoints_require_admin
- PUT /me/payout per metode & GET /me/payout termask: test_me_payout_validation_per_method
- /creator-dashboard/ tanpa key gross/net/net80/split/price:
  test_creator_dashboard_never_leaks_internal_money
- PUT /settings validasi & fee langsung mengubah creator_summary:
  test_settings_get_put_and_validation, test_fee_change_updates_creator_summary,
  test_fee_setting_changes_summary

Payout per bulan (§4 POST /payouts):
- bulan berjalan ditolak: test_create_payout_rejects_current_month
- bulan sudah dibayar ditolak: test_create_payout_rejects_paid_month_and_month_without_earnings,
  test_create_payout_duplicate_month_blocked_by_unique_index
- nominal server = share bulan itu, amount_usd di body 422: test_payout_amount_is_computed_by_server
- format_idr(2036925) == "Rp2.036.925,00": test_format_idr_always_two_decimals
"""
import io
import json
import re
import smtplib

import pytest
from pypdf import PdfReader
from sqlalchemy.exc import IntegrityError

import auth
import earnings
import gdrive
import mailer
import models
import payout_slip
from database import SessionLocal

CREATOR_PASSWORD = "creator-password"


def add_creator(db, email="creator@example.com", name="Kreator", **fields):
    creator = models.User(
        name=name,
        email=email,
        role="Creator",
        job_title="Builder",
        password=auth.get_password_hash(CREATOR_PASSWORD),
        account_status="Active",
        **fields,
    )
    db.add(creator)
    db.flush()
    return creator


def add_content(db, name="Royal Mansion", price=0.75, splits=(), sales=()):
    """splits: [(user, pct)]; sales: [(date, units, gross_usd, net80_usd)]."""
    content = models.Content(name=name, price=price, status="Published")
    db.add(content)
    db.flush()
    db.add_all(
        models.CreatorSplit(user_id=u.id, content_id=content.id, split_percentage=pct)
        for u, pct in splits
    )
    db.add_all(
        models.DailySales(date=d, content_id=content.id, quantity=q, gross_usd=g, net80_usd=n)
        for d, q, g, n in sales
    )
    db.flush()
    return content


def add_payout(db, user, amount_usd, paid_at="2026-11-01", period_month=None):
    """period_month None = payout lama (sebelum payout per bulan)."""
    payout = models.Payout(
        user_id=user.id,
        period_month=period_month,
        amount_usd=amount_usd,
        method="paypal",
        details="{}",
        paid_at=paid_at,
        created_at="2026-11-01T00:00:00+00:00",
    )
    db.add(payout)
    db.flush()
    return payout


# ============================================================================
# RUMUS (earnings.py)
# ============================================================================

def test_money_chain_gross_net80_net_share(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        content = add_content(db, splits=[(creator, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])

        [row] = earnings.content_rows(db)
        assert row["content_id"] == content.id
        assert row["month"] == "2026-10"
        assert (row["units"], row["gross_usd"], row["net80_usd"]) == (10, 100.0, 80.0)
        assert row["net_usd"] == pytest.approx(76.0)  # fee PayPal default 5%

        summary = earnings.creator_summary(db, creator, include_internal=False)
        assert summary["total_earned_usd"] == 22.8
        assert summary["outstanding_usd"] == 22.8
        assert summary["by_content"] == [
            {"content_id": content.id, "name": "Royal Mansion", "status": "Published", "units": 10, "share_usd": 22.8}
        ]
        assert summary["by_month"] == [{"month": "2026-10", "units": 10, "share_usd": 22.8}]


def test_outstanding_decreases_after_payout(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        add_content(db, splits=[(creator, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])
        add_payout(db, creator, 20.0)

        summary = earnings.creator_summary(db, creator, include_internal=False)
        assert summary["total_earned_usd"] == 22.8
        assert summary["total_paid_usd"] == 20.0
        assert summary["outstanding_usd"] == 2.8
        assert [p["amount_usd"] for p in summary["payouts"]] == [20.0]


def test_fallback_price_for_rows_without_pathway_amounts(client):
    # Angka Royal Mansion dari §7: 6.396 unit × $0,75, split 30%.
    with SessionLocal() as db:
        creator = add_creator(db)
        add_content(db, splits=[(creator, 30)], sales=[("2026-09-01", 6000, None, None), ("2026-09-02", 396, None, None)])

        [row] = earnings.content_rows(db)
        assert row["gross_usd"] == pytest.approx(4797.0)
        assert row["net80_usd"] == pytest.approx(3837.6)
        assert row["net_usd"] == pytest.approx(3645.72)
        assert earnings.creator_summary(db, creator, include_internal=False)["total_earned_usd"] == 1093.72


def test_pathway_amounts_win_over_price(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        # Harga konten 0,75 tapi Pathway melaporkan gross 1,00 (mis. diskon/kurs).
        add_content(db, splits=[(creator, 50)], sales=[("2026-10-01", 1, 1.0, 0.8), ("2026-10-02", 2, None, None)])
        [row] = earnings.content_rows(db)
        assert row["gross_usd"] == pytest.approx(1.0 + 2 * 0.75)
        assert row["net80_usd"] == pytest.approx(0.8 + 2 * 0.75 * 0.8)


def test_zero_from_pathway_is_not_replaced_by_price(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        # Hari promo gratis: unit terjual, Pathway melaporkan $0.
        add_content(db, splits=[(creator, 30)], sales=[("2026-10-01", 50, 0.0, 0.0), ("2026-10-02", 10, 7.5, 6.0)])
        [row] = earnings.content_rows(db)
        assert (row["units"], row["gross_usd"], row["net80_usd"]) == (60, 7.5, 6.0)
        assert earnings.creator_summary(db, creator, include_internal=False)["total_earned_usd"] == 1.71  # 6 × 0,95 × 30%


def test_content_rows_filters_by_user_and_month(client):
    with SessionLocal() as db:
        a = add_creator(db, "a@example.com", "A")
        b = add_creator(db, "b@example.com", "B")
        ca = add_content(db, "Konten A", splits=[(a, 30)], sales=[("2026-09-30", 1, 1, 0.8), ("2026-10-01", 2, 2, 1.6)])
        add_content(db, "Konten B", splits=[(b, 30)], sales=[("2026-10-01", 5, 5, 4)])

        assert {(r["content_id"], r["month"]) for r in earnings.content_rows(db, user_id=a.id)} == {
            (ca.id, "2026-09"),
            (ca.id, "2026-10"),
        }
        assert sum(r["units"] for r in earnings.content_rows(db, month="2026-10")) == 7


def test_fee_setting_changes_summary(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        add_content(db, splits=[(creator, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])
        earnings.set_setting(db, "paypal_fee_pct", 10)
        earnings.set_setting(db, "idr_rate", 15000)
        db.flush()

        assert earnings.paypal_fee_pct(db) == 10.0
        summary = earnings.creator_summary(db, creator, include_internal=True)
        assert summary["total_earned_usd"] == 21.6  # 80 × 0,9 × 30%
        assert summary["idr_rate"] == 15000.0
        assert summary["by_content"][0]["net_usd"] == 72.0


def test_idr_amounts_only_for_rupiah_methods(client):
    idr_keys = ("total_earned_idr", "total_paid_idr", "outstanding_idr")
    with SessionLocal() as db:
        creator = add_creator(db)
        add_content(db, splits=[(creator, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])
        add_payout(db, creator, 2.8)

        for method in (None, "paypal"):
            creator.payout_method = method
            summary = earnings.creator_summary(db, creator, False)
            assert [summary[k] for k in idr_keys] == [None, None, None], method
        for method in ("bank", "ewallet"):
            creator.payout_method = method
            summary = earnings.creator_summary(db, creator, False)
            # 22,8 / 2,8 / 20 × 16.500
            assert [summary[k] for k in idr_keys] == [376200.0, 46200.0, 330000.0], method


def test_creator_summary_internal_fields_only_for_admin(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        add_content(db, splits=[(creator, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])

        public = earnings.creator_summary(db, creator, include_internal=False)
        internal = earnings.creator_summary(db, creator, include_internal=True)
        assert set(public["by_content"][0]) == {"content_id", "name", "status", "units", "share_usd"}
        assert internal["by_content"][0]["gross_usd"] == 100.0
        assert internal["by_content"][0]["net_usd"] == 76.0
        assert internal["by_content"][0]["split_pct"] == 30
        assert internal["by_month"][0]["gross_usd"] == 100.0


def test_linked_content_without_sales_is_listed(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        add_content(db, "Belum Rilis", splits=[(creator, 40)])
        summary = earnings.creator_summary(db, creator, include_internal=False)
        assert summary["by_content"][0]["units"] == 0
        assert summary["by_content"][0]["share_usd"] == 0.0
        assert summary["by_month"] == []


def test_admin_overview_splits_net_between_creators_and_squareclouds(client):
    with SessionLocal() as db:
        a = add_creator(db, "a@example.com", "A")
        b = add_creator(db, "b@example.com", "B")
        c1 = add_content(db, "Konten 1", splits=[(a, 30), (b, 20)],
                         sales=[("2026-09-01", 5, 50.0, 40.0), ("2026-10-01", 5, 50.0, 40.0)])
        c2 = add_content(db, "Konten 2", sales=[("2026-10-01", 1, 10.0, 8.0)])

        overview = earnings.admin_overview(db)
        assert overview["totals"] == {
            "units": 11,
            "gross_usd": 110.0,
            "net80_usd": 88.0,
            "net_usd": 83.6,
            "creators_share_usd": 38.0,  # 76 × 50%
            "squareclouds_share_usd": 45.6,  # 38 + seluruh net Konten 2 (7,6)
        }
        content1, content2 = overview["by_content"]
        assert content1["content_id"] == c1.id
        assert [(c["name"], c["split_pct"], c["share_usd"]) for c in content1["creators"]] == [
            ("A", 30, 22.8),
            ("B", 20, 15.2),
        ]
        assert content2["content_id"] == c2.id
        assert content2["creators"] == []
        assert content2["squareclouds_share_usd"] == 7.6

        october, september = overview["by_month"]
        assert october["month"] == "2026-10"
        assert october["net_usd"] == 45.6
        assert [c["content_id"] for c in october["by_content"]] == [c1.id, c2.id]
        assert september["by_content"][0]["creators"][0]["share_usd"] == 11.4

        only_september = earnings.admin_overview(db, month="2026-09")
        assert only_september["totals"]["net_usd"] == 38.0
        assert [m["month"] for m in only_september["by_month"]] == ["2026-09"]


def test_format_idr_always_two_decimals():
    assert earnings.format_idr(2036925) == "Rp2.036.925,00"
    assert earnings.format_idr(16500) == "Rp16.500,00"
    assert earnings.format_idr(16250.5) == "Rp16.250,50"
    assert earnings.format_idr(999.999) == "Rp1.000,00"
    assert earnings.format_idr(0) == "Rp0,00"
    assert earnings.format_idr(-0.001) == "Rp0,00"
    assert earnings.format_idr(-1234.5) == "-Rp1.234,50"


def test_shift_month_and_last_complete_month(client):
    assert earnings.shift_month("2026-01", -1) == "2025-12"
    assert earnings.shift_month("2026-12", 1) == "2027-01"
    assert earnings.shift_month("2026-10", 0) == "2026-10"
    with SessionLocal() as db:
        assert earnings.last_complete_month(db) is None
        add_content(db, sales=[("2026-10-31", 1, 1.0, 0.8), ("2026-11-05", 1, 1.0, 0.8)])
        assert earnings.last_complete_month(db) == "2026-10"
        add_content(db, "Lain", sales=[("2027-01-01", 1, 1.0, 0.8)])
        assert earnings.last_complete_month(db) == "2026-12"


def test_creator_months_from_first_earning_to_last_complete_month(client):
    with SessionLocal() as db:
        creator = add_creator(db, payout_method="bank")
        content = add_content(db, splits=[(creator, 30)], sales=[
            ("2026-06-10", 3, 0.0, 0.0),      # unit tanpa pendapatan: belum awal rentang
            ("2026-07-05", 10, 100.0, 80.0),  # 22,8
            # Agustus kosong: tetap ada (0) karena di dalam rentang.
            ("2026-09-05", 5, 50.0, 40.0),    # 11,4
            ("2026-10-31", 1, 10.0, 8.0),     # 2,28
            ("2026-11-05", 10, 100.0, 80.0),  # bulan berjalan: tidak ditawarkan
        ])
        july = add_payout(db, creator, 22.8, period_month="2026-07")

        def items(units, net80, net, share):
            return [{"content_id": content.id, "name": "Royal Mansion", "units": units,
                     "net80_usd": net80, "net_usd": net, "split_pct": 30, "share_usd": share}]

        months = earnings.creator_months(db, creator)
        assert months == [
            {"month": "2026-07", "units": 10, "share_usd": 22.8, "share_idr": 376200.0, "paid": True,
             "payout_id": july.id, "items": items(10, 80.0, 76.0, 22.8)},
            {"month": "2026-08", "units": 0, "share_usd": 0.0, "share_idr": 0.0, "paid": False,
             "payout_id": None, "items": []},
            {"month": "2026-09", "units": 5, "share_usd": 11.4, "share_idr": 188100.0, "paid": False,
             "payout_id": None, "items": items(5, 40.0, 38.0, 11.4)},
            {"month": "2026-10", "units": 1, "share_usd": 2.28, "share_idr": 37620.0, "paid": False,
             "payout_id": None, "items": items(1, 8.0, 7.6, 2.28)},
        ]

        for method in ("paypal", None):
            creator.payout_method = method
            assert [m["share_idr"] for m in earnings.creator_months(db, creator)] == [None] * 4, method

        # outstanding tetap total share − total dibayar (termasuk bulan berjalan).
        summary = earnings.creator_summary(db, creator, include_internal=False)
        assert summary["outstanding_usd"] == pytest.approx(22.8 + 11.4 + 2.28 + 22.8 - 22.8)


def test_creator_months_empty_without_complete_earning_month(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        assert earnings.creator_months(db, creator) == []  # belum ada daily_sales sama sekali
        # Hanya bulan berjalan yang punya pendapatan.
        add_content(db, splits=[(creator, 30)], sales=[("2026-11-02", 10, 100.0, 80.0)])
        assert earnings.creator_months(db, creator) == []


def test_allocate_cents_sums_to_rounded_total():
    # Dibulatkan satu per satu: 0,33 × 3 = 0,99 dan 0,28 × 2 = 0,56 (meleset sesen).
    assert earnings.allocate_cents([1 / 3, 1 / 3, 1 / 3]) == [0.34, 0.33, 0.33]
    assert earnings.allocate_cents([0.285, 0.285]) == [0.29, 0.28]
    assert earnings.allocate_cents([22.8, 11.4]) == [22.8, 11.4]
    assert earnings.allocate_cents([0.0, 0.0]) == [0.0, 0.0]
    assert earnings.allocate_cents([]) == []
    for values in ([0.004] * 7, [1.005, 2.675, 0.125], [123.456, 0.001, 9.999]):
        cents = sum(round(v * 100) for v in earnings.allocate_cents(values))
        assert cents == round(earnings.money(sum(values)) * 100), values


def test_creator_months_items_per_content(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        # Masing-masing 1 × 0,95 × 30% = 0,285: dibulatkan sendiri-sendiri jadi
        # 0,28 + 0,28, padahal totalnya 0,57.
        b = add_content(db, "Konten B", splits=[(creator, 30)], sales=[("2026-10-05", 1, 1.25, 1.0)])
        a = add_content(db, "Konten A", splits=[(creator, 30)], sales=[("2026-10-06", 1, 1.25, 1.0)])
        add_content(db, "Tanpa Penjualan Oktober", splits=[(creator, 30)], sales=[("2026-11-05", 2, 2.5, 2.0)])

        [october] = earnings.creator_months(db, creator)
        assert october["share_usd"] == 0.57
        assert october["units"] == 2
        assert october["items"] == [
            {"content_id": a.id, "name": "Konten A", "units": 1,
             "net80_usd": 1.0, "net_usd": 0.95, "split_pct": 30, "share_usd": 0.29},
            {"content_id": b.id, "name": "Konten B", "units": 1,
             "net80_usd": 1.0, "net_usd": 0.95, "split_pct": 30, "share_usd": 0.28},
        ]


def test_unique_payout_per_creator_per_month(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        # Payout lama tanpa periode boleh lebih dari satu.
        add_payout(db, creator, 1.0)
        add_payout(db, creator, 2.0)
        add_payout(db, creator, 3.0, period_month="2026-10")
        db.commit()
        with pytest.raises(IntegrityError):
            add_payout(db, creator, 3.0, period_month="2026-10")


# ============================================================================
# ENDPOINT ADMIN
# ============================================================================

BANK = {"bank_name": "BCA", "account_number": "1234567890", "account_name": "Kreator Satu"}


def login(client, email="creator@example.com"):
    res = client.post("/login", data={"username": email, "password": CREATOR_PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


OCTOBER_SALE = ("2026-10-05", 10, 100.0, 80.0)  # gross 100, net80 80 -> share 30% = 22,8


def seed_creator(method=None, details=None, sales=(OCTOBER_SALE,), data_until="2026-11-05", username="kreator"):
    """Kreator Active dengan satu konten (split 30%); default share Oktober 2026 = 22,8.

    data_until: tanggal penjualan terakhir di daily_sales, lewat konten lain
    tanpa kreator. Default 5 November, jadi Oktober = bulan lengkap terakhir
    dan bisa dibayar. None = tanpa konten tambahan itu.
    """
    with SessionLocal() as db:
        creator = add_creator(
            db,
            username=username,
            payout_method=method,
            payout_details=None if details is None else json.dumps(details),
        )
        add_content(db, splits=[(creator, 30)], sales=sales)
        if data_until:
            add_content(db, "Konten Tanpa Kreator", sales=[(data_until, 1, 1.0, 0.8)])
        db.commit()
        return creator.id


def post_payout(client, headers, user_id, period_month="2026-10", **body):
    return client.post("/payouts", json={"user_id": user_id, "period_month": period_month, **body}, headers=headers)


DEFAULT_ADDRESS = "Jalan Halat, Gang Merdeka No.12\nKecamatan Medan Area, Kota Medan\nSumatera Utara 20216"


def test_settings_get_put_and_validation(client, admin_headers):
    def get_settings():
        return client.get("/settings", headers=admin_headers).json()

    assert get_settings() == {"paypal_fee_pct": 5.0, "idr_rate": 16500.0, "company_address": DEFAULT_ADDRESS}

    res = client.put("/settings", json={"paypal_fee_pct": 3.5, "idr_rate": 16250.5}, headers=admin_headers)
    assert res.status_code == 200, res.text
    # Tanpa company_address: alamat tidak berubah.
    expected = {"paypal_fee_pct": 3.5, "idr_rate": 16250.5, "company_address": DEFAULT_ADDRESS}
    assert res.json()["data"] == expected
    assert get_settings() == expected

    for body in (
        {"paypal_fee_pct": -0.1, "idr_rate": 16500},
        {"paypal_fee_pct": 100.1, "idr_rate": 16500},
        {"paypal_fee_pct": 5, "idr_rate": 0},
        {"paypal_fee_pct": 5, "idr_rate": -1},
    ):
        assert client.put("/settings", json=body, headers=admin_headers).status_code == 400, body
    assert client.put("/settings", json={"paypal_fee_pct": 5}, headers=admin_headers).status_code == 422
    assert get_settings() == expected

    # Batas 0 dan 100 boleh.
    for fee in (0, 100):
        body = {"paypal_fee_pct": fee, "idr_rate": 1}
        assert client.put("/settings", json=body, headers=admin_headers).status_code == 200
    assert get_settings() == {"paypal_fee_pct": 100.0, "idr_rate": 1.0, "company_address": DEFAULT_ADDRESS}


def test_settings_company_address(client, admin_headers):
    base = {"paypal_fee_pct": 5, "idr_rate": 16500}
    body = {**base, "company_address": "  Jl. Baru No. 1 \r\n\n  Medan 20111  \n"}
    res = client.put("/settings", json=body, headers=admin_headers)
    assert res.status_code == 200, res.text
    # Spasi di tepi dan baris kosong dibuang.
    assert res.json()["data"]["company_address"] == "Jl. Baru No. 1\nMedan 20111"

    # Maksimal 3 baris (sama dengan blok pengirim slip) dan 300 karakter.
    for address in ("", "  \n  ", "\n".join(f"Baris {i}" for i in range(4)), "x" * 301):
        res = client.put("/settings", json={**base, "company_address": address}, headers=admin_headers)
        assert res.status_code == 400, address
    assert client.get("/settings", headers=admin_headers).json()["company_address"] == "Jl. Baru No. 1\nMedan 20111"


def test_settings_and_payout_endpoints_require_admin(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    headers = login(client)

    assert client.get("/settings", headers=headers).status_code == 403
    assert client.put("/settings", json={"paypal_fee_pct": 0, "idr_rate": 1}, headers=headers).status_code == 403
    assert client.get(f"/users/{creator_id}/earnings", headers=headers).status_code == 403
    assert post_payout(client, headers, creator_id).status_code == 403
    assert client.delete(f"/payouts/{payout_id}", headers=headers).status_code == 403
    assert client.get("/settings").status_code == 401
    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 1


def test_fee_change_updates_creator_summary(client, admin_headers):
    creator_id = seed_creator()
    url = f"/users/{creator_id}/earnings"
    assert client.get(url, headers=admin_headers).json()["total_earned_usd"] == 22.8

    client.put("/settings", json={"paypal_fee_pct": 10, "idr_rate": 16500}, headers=admin_headers)
    assert client.get(url, headers=admin_headers).json()["total_earned_usd"] == 21.6  # 80 × 0,9 × 30%
    assert client.get("/creator-dashboard/", headers=login(client)).json()["total_earned_usd"] == 21.6


def test_user_earnings_has_internal_fields_and_full_details(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    data = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()
    assert data["payout_method"] == "bank"
    assert data["payout_details"] == BANK
    assert data["by_content"][0]["gross_usd"] == 100.0
    assert data["by_content"][0]["net_usd"] == 76.0
    assert data["by_content"][0]["split_pct"] == 30
    assert data["outstanding_idr"] == 376200.0
    content_id = data["by_content"][0]["content_id"]
    assert data["months"] == [
        {"month": "2026-10", "units": 10, "share_usd": 22.8, "share_idr": 376200.0, "paid": False, "payout_id": None,
         "items": [{"content_id": content_id, "name": "Royal Mansion", "units": 10,
                    "net80_usd": 80.0, "net_usd": 76.0, "split_pct": 30, "share_usd": 22.8}]}
    ]

    with SessionLocal() as db:
        admin_id = db.query(models.User.id).filter(models.User.role == "Admin").scalar()
    assert client.get(f"/users/{admin_id}/earnings", headers=admin_headers).status_code == 400
    assert client.get("/users/999/earnings", headers=admin_headers).status_code == 404


SEPT_OCT_NOV = (
    ("2026-09-05", 10, 100.0, 80.0),  # September: 22,8
    ("2026-10-05", 5, 50.0, 40.0),    # Oktober: 11,4
    ("2026-11-05", 10, 100.0, 80.0),  # November (bulan berjalan): 22,8
)


def test_create_payout_snapshots_method_and_reduces_outstanding(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK, sales=SEPT_OCT_NOV)
    res = post_payout(client, admin_headers, creator_id, "2026-09", note="  September  ", paid_at="2026-10-03")
    assert res.status_code == 201, res.text
    assert res.json()["message"].startswith("Payout September 2026 ($22.80) untuk Kreator dicatat.")
    payout = res.json()["data"]
    assert payout["period_month"] == "2026-09"
    assert payout["amount_usd"] == 22.8
    assert payout["idr_rate"] == 16500.0
    assert payout["amount_idr"] == 376200.0
    assert payout["method"] == "bank"
    assert payout["details"] == BANK
    assert payout["note"] == "September"
    assert payout["paid_at"] == "2026-10-03"

    # Kreator ganti metode setelahnya: snapshot di payout lama tidak berubah.
    paypal = {"payout_method": "paypal", "payout_details": {"paypal_email": "k@pp.com"}}
    assert client.put("/me/payout", json=paypal, headers=login(client)).status_code == 200
    data = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()
    assert data["total_paid_usd"] == 22.8
    assert data["outstanding_usd"] == 34.2  # Oktober + November
    assert data["outstanding_idr"] is None
    assert data["payouts"][0]["details"] == BANK
    assert [(m["month"], m["paid"], m["share_idr"]) for m in data["months"]] == [
        ("2026-09", True, None),
        ("2026-10", False, None),
    ]

    # PayPal: tanpa amount_idr.
    res = post_payout(client, admin_headers, creator_id, "2026-10")
    assert res.status_code == 201, res.text
    assert res.json()["data"]["amount_usd"] == 11.4
    assert res.json()["data"]["amount_idr"] is None
    assert res.json()["data"]["method"] == "paypal"
    # Tinggal November, yang belum bisa dibayar.
    assert client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()["outstanding_usd"] == 22.8


def test_payout_amount_is_computed_by_server(client, admin_headers):
    creator_id = seed_creator(method="ewallet", details={"provider": "OVO", "phone": "081234567890", "account_name": "K"},
                              sales=SEPT_OCT_NOV)
    body = {"user_id": creator_id, "period_month": "2026-10"}

    # Jumlah tidak bisa diisi manual.
    for extra in ({"amount_usd": 11.4}, {"amount_usd": 999}, {"amount_idr": 1}):
        assert client.post("/payouts", json={**body, **extra}, headers=admin_headers).status_code == 422, extra
    assert client.post("/payouts", json={"user_id": creator_id}, headers=admin_headers).status_code == 422

    # Bagian Oktober saja, bukan saldo tertunda (57,0) atau bulan lain.
    res = client.post("/payouts", json=body, headers=admin_headers)
    assert res.status_code == 201, res.text
    assert (res.json()["data"]["amount_usd"], res.json()["data"]["amount_idr"]) == (11.4, 188100.0)
    with SessionLocal() as db:
        [payout] = db.query(models.Payout).all()
        assert (payout.period_month, payout.amount_usd, payout.amount_idr) == ("2026-10", 11.4, 188100.0)


def test_create_payout_rejects_current_month(client, admin_headers):
    # Data terakhir 5 November: November masih berjalan, Desember belum ada.
    creator_id = seed_creator(method="bank", details=BANK, sales=SEPT_OCT_NOV)
    for period in ("2026-11", "2026-12"):
        res = post_payout(client, admin_headers, creator_id, period)
        assert res.status_code == 400, period
        assert "belum lengkap" in res.json()["detail"]
    assert "November 2026 belum lengkap" in post_payout(client, admin_headers, creator_id, "2026-11").json()["detail"]
    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 0


def test_create_payout_rejects_paid_month_and_month_without_earnings(client, admin_headers):
    # Agustus kosong di antara Juli dan September.
    sales = (("2026-07-05", 10, 100.0, 80.0), ("2026-09-05", 5, 50.0, 40.0))
    creator_id = seed_creator(method="bank", details=BANK, sales=sales)
    july_id = post_payout(client, admin_headers, creator_id, "2026-07").json()["data"]["id"]

    res = post_payout(client, admin_headers, creator_id, "2026-07")
    assert res.status_code == 400
    assert res.json()["detail"] == "Periode Juli 2026 sudah dibayar."
    for period, label in (("2026-08", "Agustus 2026"), ("2026-06", "Juni 2026")):
        res = post_payout(client, admin_headers, creator_id, period)
        assert res.status_code == 400, period
        assert res.json()["detail"] == f"Tidak ada pendapatan untuk periode {label}."

    months = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()["months"]
    assert [(m["month"], m["share_usd"], m["paid"], m["payout_id"]) for m in months] == [
        ("2026-07", 22.8, True, july_id),
        ("2026-08", 0.0, False, None),
        ("2026-09", 11.4, False, None),
        ("2026-10", 0.0, False, None),
    ]
    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 1


def test_create_payout_duplicate_month_blocked_by_unique_index(client, admin_headers, monkeypatch):
    # Seolah dua admin mencatat bersamaan: cek "sudah dibayar" sama-sama lolos,
    # unique index (user_id, period_month) yang menolak.
    creator_id = seed_creator(method="bank", details=BANK, sales=(OCTOBER_SALE, ("2026-11-05", 10, 100.0, 80.0)))
    assert post_payout(client, admin_headers, creator_id).status_code == 201

    real_creator_months = earnings.creator_months
    monkeypatch.setattr(
        earnings, "creator_months", lambda db, user: [{**m, "paid": False} for m in real_creator_months(db, user)]
    )
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 400
    assert res.json()["detail"] == "Periode Oktober 2026 sudah dibayar."
    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 1


def test_create_payout_rejections(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)

    for period in ("2026-13", "2026-00", "10-2026", "2026-1", "", "2026-10-01"):
        res = post_payout(client, admin_headers, creator_id, period)
        assert res.status_code == 400, period
        assert res.json()["detail"] == "Periode harus berformat YYYY-MM."
    assert post_payout(client, admin_headers, creator_id, paid_at="03-11-2026").status_code == 400
    assert post_payout(client, admin_headers, 999).status_code == 404

    with SessionLocal() as db:
        no_method = add_creator(db, "nomethod@example.com")
        add_content(db, "Konten Lain", splits=[(no_method, 30)], sales=[OCTOBER_SALE])
        inactive = add_creator(
            db, "inactive@example.com", payout_method="bank", payout_details=json.dumps(BANK)
        )
        inactive.account_status = "Inactive"
        db.commit()
        no_method_id, inactive_id = no_method.id, inactive.id

    res = post_payout(client, admin_headers, no_method_id)
    assert res.status_code == 400
    assert res.json()["detail"] == "Kreator belum mengisi metode payout."
    assert post_payout(client, admin_headers, inactive_id).status_code == 400

    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 0


def test_legacy_payout_without_period_still_limits_outstanding(client, admin_headers):
    # Payout lama (sebelum payout per bulan) tidak menandai bulan mana pun
    # sebagai dibayar, tapi tetap mengurangi saldo tertunda.
    creator_id = seed_creator(method="bank", details=BANK)
    with SessionLocal() as db:
        add_payout(db, db.get(models.User, creator_id), 20.0)
        db.commit()

    data = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()
    assert data["outstanding_usd"] == 2.8
    assert data["months"][0]["paid"] is False
    assert data["payouts"][0]["period_month"] is None
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 400
    assert "melebihi saldo tertunda ($2.80)" in res.json()["detail"]


def test_delete_payout_restores_outstanding(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id)
    payout_id = res.json()["data"]["id"]
    assert client.delete(f"/payouts/{payout_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/payouts/{payout_id}", headers=admin_headers).status_code == 404
    data = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()
    assert data["outstanding_usd"] == 22.8
    assert data["months"][0]["paid"] is False
    # Bulannya bisa dicatat ulang setelah koreksi.
    assert post_payout(client, admin_headers, creator_id).status_code == 201


def test_delete_creator_also_deletes_payouts(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    post_payout(client, admin_headers, creator_id)
    assert client.delete(f"/users/{creator_id}", headers=admin_headers).status_code == 200
    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 0
        assert db.query(models.PayoutItem).count() == 0


def seed_two_content_creator():
    """Kreator bank dengan dua konten di Oktober, masing-masing share 0,285
    (total 0,57): pembulatan per konten harus tetap pas dengan total."""
    with SessionLocal() as db:
        creator = add_creator(db, username="kreator", payout_method="bank", payout_details=json.dumps(BANK))
        add_content(db, "Konten B", splits=[(creator, 30)], sales=[("2026-10-05", 1, 1.25, 1.0)])
        add_content(db, "Konten A", splits=[(creator, 30)], sales=[("2026-10-06", 1, 1.25, 1.0)])
        add_content(db, "Konten Tanpa Kreator", sales=[("2026-11-05", 1, 1.0, 0.8)])
        db.commit()
        return creator.id


def test_payout_items_saved_and_sum_to_amount(client, admin_headers):
    creator_id = seed_two_content_creator()
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 201, res.text
    payout_id = res.json()["data"]["id"]

    with SessionLocal() as db:
        payout = db.get(models.Payout, payout_id)
        assert payout.amount_usd == 0.57
        rows = [(i.content_name, i.units, i.net80_usd, i.net_usd, i.split_pct, i.share_usd) for i in payout.items]
        assert rows == [("Konten A", 1, 1.0, 0.95, 30.0, 0.29), ("Konten B", 1, 1.0, 0.95, 30.0, 0.28)]
        assert round(sum(i.share_usd for i in payout.items), 2) == payout.amount_usd
        assert payout.paypal_fee_pct == 5.0
        content_ids = {c.name: c.id for c in db.query(models.Content)}
        assert [i.content_id for i in payout.items] == [content_ids["Konten A"], content_ids["Konten B"]]

    # Snapshot: ganti nama konten dan split setelahnya tidak mengubah rincian.
    with SessionLocal() as db:
        content = db.query(models.Content).filter(models.Content.name == "Konten A").one()
        content.name = "Konten A (baru)"
        db.query(models.CreatorSplit).update({models.CreatorSplit.split_percentage: 50})
        db.commit()
    with SessionLocal() as db:
        rows = [(i.content_name, i.share_usd, i.split_pct) for i in db.get(models.Payout, payout_id).items]
        assert rows == [("Konten A", 0.29, 30.0), ("Konten B", 0.28, 30.0)]


def test_payout_detail_and_pdf_endpoints_are_gone(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    # Slip hanya dikirim lewat email (dan arsip Drive), tidak bisa diunduh.
    # /payouts/{id} masih punya DELETE, jadi GET-nya 405; /pdf tidak ada sama sekali.
    for headers in (admin_headers, login(client)):
        assert client.get(f"/payouts/{payout_id}", headers=headers).status_code == 405
        assert client.get(f"/payouts/{payout_id}/pdf", headers=headers).status_code == 404


def test_deleting_payout_deletes_its_items(client, admin_headers):
    creator_id = seed_two_content_creator()
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    assert client.delete(f"/payouts/{payout_id}", headers=admin_headers).status_code == 200
    with SessionLocal() as db:
        assert db.query(models.PayoutItem).count() == 0


def test_admin_reports_and_contents_use_overview(client, admin_headers):
    seed_creator(data_until=None)
    report = client.get("/admin-reports/", headers=admin_headers).json()["data"]
    assert report["totals"]["net_usd"] == 76.0
    assert report["totals"]["creators_share_usd"] == 22.8
    assert report["totals"]["squareclouds_share_usd"] == 53.2
    [month] = report["by_month"]
    assert month["month"] == "2026-10"
    assert month["by_content"][0]["squareclouds_share_usd"] == 53.2
    assert client.get("/admin-reports/?month=2026-09", headers=admin_headers).json()["data"]["by_month"] == []

    [content] = client.get("/contents/", headers=admin_headers).json()["data"]
    assert (content["units_total"], content["gross_usd"], content["net_usd"]) == (10, 100.0, 76.0)


# ============================================================================
# ENDPOINT KREATOR
# ============================================================================

def put_payout(client, headers, method, details):
    body = {"payout_method": method, "payout_details": details}
    return client.put("/me/payout", json=body, headers=headers)


def test_me_payout_validation_per_method(client):
    seed_creator()
    headers = login(client)
    assert client.get("/me/payout", headers=headers).json() == {"payout_method": None, "payout_details_masked": None}

    ewallet = {"provider": "DANA", "phone": "081234567890", "account_name": "K"}
    invalid = [
        ("paypal", {"paypal_email": "bukan-email"}),
        ("paypal", {}),
        ("bank", {**BANK, "account_number": "12345"}),
        ("bank", {**BANK, "account_number": "1" * 21}),
        ("bank", {**BANK, "account_number": "12345abc"}),
        ("bank", {**BANK, "account_name": "  "}),
        ("bank", {**BANK, "bank_name": ""}),
        ("ewallet", {**ewallet, "provider": "LinkAja"}),
        ("ewallet", {**ewallet, "phone": "081234567"}),  # 9 digit
        ("ewallet", {**ewallet, "phone": "08123456789012"}),  # 14 digit
        ("ewallet", {**ewallet, "phone": "071234567890"}),  # bukan nomor HP
        ("ewallet", {"provider": "DANA", "phone": "081234567890"}),  # tanpa account_name
        ("crypto", {"wallet": "x"}),
    ]
    for method, details in invalid:
        assert put_payout(client, headers, method, details).status_code == 400, (method, details)
    assert client.get("/me/payout", headers=headers).json()["payout_method"] is None

    res = put_payout(client, headers, "paypal", {"paypal_email": " Kreator@PayPal.com ", "extra": "dibuang"})
    assert res.status_code == 200, res.text
    assert res.json()["payout_details_masked"] == {"paypal_email": "kr***@paypal.com"}
    res = put_payout(client, headers, "paypal", {"paypal_email": "a@b.co"})
    assert res.json()["payout_details_masked"] == {"paypal_email": "a***@b.co"}

    res = put_payout(client, headers, "bank", {**BANK, "account_number": "1234-5678 90"})
    assert res.status_code == 200, res.text
    assert res.json()["payout_details_masked"] == {**BANK, "account_number": "******7890"}

    res = put_payout(client, headers, "ewallet", {**ewallet, "provider": "GoPay", "phone": "+62 812-3456-7890"})
    assert res.status_code == 200, res.text
    masked = {"provider": "GoPay", "phone": "********7890", "account_name": "K"}
    assert res.json()["payout_details_masked"] == masked
    assert client.get("/me/payout", headers=headers).json() == {"payout_method": "ewallet", "payout_details_masked": masked}

    with SessionLocal() as db:
        creator = db.query(models.User).filter(models.User.role == "Creator").one()
        assert earnings.load_details(creator.payout_details)["phone"] == "081234567890"


def test_me_payout_only_for_creators(client, admin_headers):
    assert client.get("/me/payout", headers=admin_headers).status_code == 403
    assert put_payout(client, admin_headers, "paypal", {"paypal_email": "a@b.co"}).status_code == 403
    assert client.get("/me/payout").status_code == 401


FORBIDDEN_KEY_PARTS = ("gross", "net", "net80", "split", "price")


def all_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from all_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from all_keys(v)


def test_creator_dashboard_never_leaks_internal_money(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK, sales=SEPT_OCT_NOV)
    post_payout(client, admin_headers, creator_id, "2026-09", note="x")

    data = client.get("/creator-dashboard/", headers=login(client)).json()
    leaked = [k for k in all_keys(data) if any(part in k.lower() for part in FORBIDDEN_KEY_PARTS)]
    assert leaked == []
    assert data["total_earned_usd"] == 57.0
    assert data["total_paid_usd"] == 22.8
    assert data["outstanding_usd"] == 34.2
    assert data["outstanding_idr"] == 564300.0  # 34,2 × 16.500
    assert data["by_content"][0]["units"] == 25
    assert data["by_month"] == [
        {"month": "2026-11", "units": 10, "share_usd": 22.8},
        {"month": "2026-10", "units": 5, "share_usd": 11.4},
        {"month": "2026-09", "units": 10, "share_usd": 22.8},
    ]
    assert data["payouts"][0]["note"] == "x"
    assert data["payouts"][0]["period_month"] == "2026-09"
    assert data["grafik_harian"] == [
        {"date": d, "content_name": "Royal Mansion", "quantity": q} for d, q, _, _ in SEPT_OCT_NOV
    ]
    assert client.get("/creator-dashboard/", headers=admin_headers).status_code == 403


def test_creator_payout_history_hides_snapshot_and_admin_fields(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    post_payout(client, admin_headers, creator_id)

    [payout] = client.get("/creator-dashboard/", headers=login(client)).json()["payouts"]
    assert set(payout) == {"id", "period_month", "paid_at", "amount_usd", "idr_rate", "amount_idr", "method", "note"}
    assert BANK["account_number"] not in str(payout)


def test_payout_idr_snapshot_survives_rate_change(client, admin_headers):
    creator_id = seed_creator(method="ewallet", details={"provider": "OVO", "phone": "081234567890", "account_name": "K"},
                              sales=SEPT_OCT_NOV)
    post_payout(client, admin_headers, creator_id, "2026-09")
    client.put("/settings", json={"paypal_fee_pct": 5, "idr_rate": 17000}, headers=admin_headers)

    data = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()
    assert (data["payouts"][0]["idr_rate"], data["payouts"][0]["amount_idr"]) == (16500.0, 376200.0)
    assert data["idr_rate"] == 17000.0
    assert data["outstanding_idr"] == 581400.0  # 34,2 × 17.000
    # Bulan yang belum dibayar ikut kurs baru: 11,4 × 17.000.
    october = data["months"][1]
    assert (october["month"], october["share_usd"], october["share_idr"], october["paid"]) == (
        "2026-10", 11.4, 193800.0, False
    )


def test_settings_reject_non_numeric(client, admin_headers):
    body = {"paypal_fee_pct": "lima", "idr_rate": 16500}
    assert client.put("/settings", json=body, headers=admin_headers).status_code == 422
    assert client.get("/settings", headers=admin_headers).json()["paypal_fee_pct"] == 5.0


# ============================================================================
# EMAIL NOTIFIKASI PAYOUT
# ============================================================================

def get_payout(payout_id):
    with SessionLocal() as db:
        return db.get(models.Payout, payout_id)


def failing_send_mail(to, subject, html, text, attachments=None):
    raise smtplib.SMTPServerDisconnected("SMTP mati")


def test_payout_sends_email_to_creator(client, admin_headers, outbox, monkeypatch):
    monkeypatch.setenv("PORTAL_URL", "https://portal.test/")
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id, note="Payout <Oktober>", paid_at="2026-11-03")
    assert res.status_code == 201, res.text
    assert res.json()["notified"] is True
    assert get_payout(res.json()["data"]["id"]).notified_at is not None

    [mail] = outbox
    assert mail["to"] == "creator@example.com"
    assert mail["subject"] == "Payout Squareclouds Studio - Oktober 2026"
    assert mail["text"] == (
        "Halo Kreator,\n"
        "\n"
        "Payout pendapatan Anda dari Squareclouds Studio telah dikirim.\n"
        "\n"
        "Periode : Oktober 2026\n"
        "Tanggal : 3 November 2026\n"
        "\n"
        "Slip payout (PDF) terlampir.\n"
        "\n"
        "Buka dashboard: https://portal.test/creator\n"
        "\n"
        "Salam,\n"
        "Squareclouds Studio"
    )
    html = mail["html"]
    for part in (
        "<p>Halo Kreator,</p>",
        ">Periode</td>",
        ">Oktober 2026</td>",
        ">Tanggal</td>",
        ">3 November 2026</td>",
        "<p>Slip payout (PDF) terlampir.</p>",
        '<a href="https://portal.test/creator"',
        ">Buka dashboard</a>",
        "Salam,<br>Squareclouds Studio",
    ):
        assert part in html, part
    assert_email_has_no_payout_details(mail)


# Hanya ada di slip PDF terlampir, tidak pernah di isi email.
EMAIL_FORBIDDEN = (
    "$", "22.80", "Rp", "kurs", "Jumlah", "Tujuan", "Catatan", "Transfer bank", "BCA", "7890",
    "PayPal", "kr***", "DANA", "****", "Royal Mansion", "Konten", "Rincian", "Payout <Oktober>", "&lt;Oktober&gt;",
)


def assert_email_has_no_payout_details(mail):
    body = mail["subject"] + mail["text"] + mail["html"]
    leaked = [word for word in EMAIL_FORBIDDEN if word in body]
    assert leaked == [], leaked


def test_payout_email_has_no_amounts_for_any_method(client, admin_headers, outbox):
    creator_id = seed_creator(method="paypal", details={"paypal_email": "kreator@gmail.com"}, sales=SEPT_OCT_NOV)
    assert post_payout(client, admin_headers, creator_id, "2026-09", note="x").status_code == 201
    assert outbox[-1]["subject"] == "Payout Squareclouds Studio - September 2026"
    assert "Periode : September 2026\n" in outbox[-1]["text"]
    assert_email_has_no_payout_details(outbox[-1])

    with SessionLocal() as db:
        creator = db.get(models.User, creator_id)
        creator.payout_method = "ewallet"
        creator.payout_details = json.dumps({"provider": "DANA", "phone": "081234565678", "account_name": "K"})
        db.commit()
    post_payout(client, admin_headers, creator_id, "2026-10")
    assert outbox[-1]["subject"] == "Payout Squareclouds Studio - Oktober 2026"
    assert_email_has_no_payout_details(outbox[-1])
    # Jumlah & rupiah tetap ada di slip terlampir.
    [(_, data, _)] = outbox[-1]["attachments"]
    assert "Rp188.100,00" in pdf_text(data)  # 11,4 × 16.500


def test_payout_email_without_period_for_legacy_payout(client, admin_headers, outbox):
    creator_id = seed_creator(method="bank", details=BANK)
    with SessionLocal() as db:
        payout_id = add_payout(db, db.get(models.User, creator_id), 5.0).id
        db.commit()
    assert client.post(f"/payouts/{payout_id}/notify", headers=admin_headers).status_code == 200
    mail = outbox[-1]
    # Tanpa periode: tanggal bayar di subjek dan nama file, baris Periode dilewati.
    assert mail["subject"] == "Payout Squareclouds Studio - 1 November 2026"
    assert "Periode" not in mail["text"] + mail["html"]
    assert "telah dikirim.\n\nTanggal : 1 November 2026\n\nSlip payout (PDF) terlampir." in mail["text"]
    [(filename, data, mime_type)] = mail["attachments"]
    assert (filename, mime_type) == ("Payout Slip - kreator - 1 November 2026.pdf", "application/pdf")
    assert data.startswith(b"%PDF")


def test_payout_email_attaches_slip_with_content_breakdown(client, admin_headers, outbox):
    creator_id = seed_two_content_creator()
    assert post_payout(client, admin_headers, creator_id).status_code == 201

    mail = outbox[-1]
    [(filename, data, mime_type)] = mail["attachments"]
    assert (filename, mime_type) == ("Payout Slip - kreator - Oktober 2026.pdf", "application/pdf")
    # Rincian per konten hanya di PDF, tidak di email.
    text = pdf_text(data)
    for part in ("Konten A", "$0.29", "Konten B", "$0.28", "$0.57"):
        assert part in text, part
    assert_email_has_no_payout_details(mail)


def test_mailer_sends_attachment_as_multipart(monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, context):
            pass

        def login(self, user, password):
            pass

        def send_message(self, msg):
            sent.append(msg)

    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    pdf = b"%PDF-1.4 test"
    assert mailer.send_mail("a@b.co", "Subjek", "<p>Halo</p>", "Halo", attachments=[("slip.pdf", pdf, "application/pdf")])

    [msg] = sent
    assert msg.get_content_type() == "multipart/mixed"
    body = msg.get_body(preferencelist=("html",))
    assert body.get_content().strip() == "<p>Halo</p>"
    [attachment] = list(msg.iter_attachments())
    assert attachment.get_content_type() == "application/pdf"
    assert attachment.get_filename() == "slip.pdf"
    assert attachment.get_content() == pdf


def test_payout_saved_when_email_fails(client, admin_headers, monkeypatch):
    monkeypatch.setattr(mailer, "send_mail", failing_send_mail)
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 201, res.text
    assert res.json()["notified"] is False
    assert res.json()["data"]["notified_at"] is None
    assert "gagal dikirim" in res.json()["message"]

    payout = get_payout(res.json()["data"]["id"])
    assert payout.notified_at is None
    assert payout.amount_usd == 22.8
    assert client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()["total_paid_usd"] == 22.8


def test_payout_without_smtp_is_not_marked_notified(client, admin_headers):
    # SMTP_HOST kosong (conftest): email hanya dicetak ke log, tidak terkirim.
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 201
    assert res.json()["notified"] is False
    assert get_payout(res.json()["data"]["id"]).notified_at is None


def test_resend_payout_email(client, admin_headers, monkeypatch):
    creator_id = seed_creator(method="bank", details=BANK)
    monkeypatch.setattr(mailer, "send_mail", failing_send_mail)
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    url = f"/payouts/{payout_id}/notify"

    # Admin-only.
    assert client.post(url).status_code == 401
    assert client.post(url, headers=login(client)).status_code == 403

    # Masih gagal -> 502, notified_at tetap NULL.
    res = client.post(url, headers=admin_headers)
    assert res.status_code == 502
    assert get_payout(payout_id).notified_at is None

    sent = []
    monkeypatch.setattr(mailer, "send_mail", lambda to, subject, html, text, attachments=None: sent.append(subject) or True)
    res = client.post(url, headers=admin_headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["notified_at"] is not None
    assert sent == ["Payout Squareclouds Studio - Oktober 2026"]

    # Sudah terkirim -> tidak dikirim dua kali.
    assert client.post(url, headers=admin_headers).status_code == 400
    assert client.post("/payouts/999/notify", headers=admin_headers).status_code == 404
    assert len(sent) == 1


# ============================================================================
# SLIP PAYOUT PDF
# ============================================================================

# Tidak boleh ada di slip kreator (huruf kecil, dicek sebagai substring). Net
# boleh tampil di slip (rantai perhitungan seperti Pathway), tapi gross dan
# bagian Squareclouds tidak pernah.
FORBIDDEN_SLIP_WORDS = (
    "gross", "bagian squareclouds", "squareclouds share", "slip no", "this slip is generated", "creator earnings",
)
# Satu-satunya "@" yang boleh ada di slip: email pengirim dan email penerima
# (keduanya memang bagian blok identitas). "@username" tidak boleh.
SLIP_EMAILS = ("contact@squarecloudsmc.com", "creator@example.com")


def pdf_pages(content):
    return [page.extract_text() for page in PdfReader(io.BytesIO(content)).pages]


def pdf_text(content):
    return "\n".join(pdf_pages(content))


def assert_no_internal_money(text):
    leaked = [word for word in FORBIDDEN_SLIP_WORDS if word in text.lower()]
    assert leaked == [], leaked


def assert_no_at_sign_outside_emails(text):
    for email in SLIP_EMAILS:
        text = text.replace(email, "")
    assert "@" not in text


def assert_consecutive_lines(text, expected):
    """expected muncul berurutan sebagai baris utuh (pypdf kadang memberi spasi
    di depan baris, dan tiap sel tabel jadi baris sendiri)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    windows = [lines[i:i + len(expected)] for i in range(len(lines))]
    assert expected in windows, lines


def sent_slip(outbox):
    """(nama file, teks PDF) slip yang dilampirkan di email terakhir."""
    [(filename, data, mime_type)] = outbox[-1]["attachments"]
    assert mime_type == "application/pdf"
    assert data.startswith(b"%PDF")
    return filename, pdf_text(data)


def regenerate_slip(payout_id):
    """Teks slip yang dibuat ulang sekarang (seperti saat kirim ulang email / upload ulang Drive)."""
    import main

    with SessionLocal() as db:
        payout = db.get(models.Payout, payout_id)
        return pdf_text(main.payout_slip_pdf(db, db.get(models.User, payout.user_id), payout))


def item_shares(payout_id):
    with SessionLocal() as db:
        return [earnings.format_usd(i.share_usd) for i in db.get(models.Payout, payout_id).items]


def test_payout_slip_content(client, admin_headers, outbox):
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id, note="Terima kasih", paid_at="2026-11-03")
    payout_id = res.json()["data"]["id"]

    filename, text = sent_slip(outbox)
    assert filename == "Payout Slip - kreator - Oktober 2026.pdf"
    for part in (
        "Created On: 3 November 2026",
        "Revenue Month: Oktober 2026",
        "Subtotal: $22.80",
        "Total: $22.80",
        "Exchange Rate: Rp16.500,00/$",
        "Total (IDR): Rp376.200,00",
        "Note: Terima kasih",
    ):
        assert part in text, part
    # Kiri: pengirim + alamat dari settings.company_address.
    assert_consecutive_lines(text, [
        "Squareclouds Studio",
        "contact@squarecloudsmc.com",
        "Jalan Halat, Gang Merdeka No.12",
        "Kecamatan Medan Area, Kota Medan",
        "Sumatera Utara 20216",
    ])
    # Kanan: nama, "<username> - Squareclouds Studio", email.
    assert_consecutive_lines(text, ["Kreator", "kreator - Squareclouds Studio", "creator@example.com"])
    # Rantai per konten: net80 80 → fee 5% (4) → net 76 × split 30% = 22,8.
    assert_consecutive_lines(text, [
        "Content", "Comment", "Price",
        "Royal Mansion (10 units)", "Total Revenues", "$80.00",
        "PayPal Fee 5.00%", "-$4.00",
        "Creator Split 30.00%", "$22.80",
        "Product Total", "$22.80",
    ])
    assert item_shares(payout_id) == ["$22.80"]  # Product Total = share_usd

    assert_no_internal_money(text)
    assert_no_at_sign_outside_emails(text)
    for absent in ("Transfer bank", "BCA", BANK["account_number"], "PO-", "Squareclouds Studio Creator"):
        assert absent not in text, absent


def test_payout_slip_matches_pathway_example(client, admin_headers, outbox):
    # Contoh slip: 1.585 unit, Total Revenues (net80) $950,99, fee 5%, split 20%.
    with SessionLocal() as db:
        creator = add_creator(db, username="kreator", payout_method="paypal",
                              payout_details=json.dumps({"paypal_email": "k@pp.com"}))
        add_content(db, splits=[(creator, 20)], sales=[("2026-10-05", 1585, 1188.74, 950.99)])
        add_content(db, "Konten Tanpa Kreator", sales=[("2026-11-05", 1, 1.0, 0.8)])
        db.commit()
        creator_id = creator.id
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]

    _, text = sent_slip(outbox)
    assert_consecutive_lines(text, [
        "Royal Mansion (1.585 units)", "Total Revenues", "$950.99",
        "PayPal Fee 5.00%", "-$47.55",
        "Creator Split 20.00%", "$180.69",
        "Product Total", "$180.69",
        "Subtotal: $180.69",
        "Total: $180.69",
    ])
    assert item_shares(payout_id) == ["$180.69"]


def test_payout_slip_block_per_content(client, admin_headers, outbox):
    creator_id = seed_two_content_creator()
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    _, text = sent_slip(outbox)
    # Product Total tiap konten = share_usd item (sen dibagi allocate_cents).
    assert item_shares(payout_id) == ["$0.29", "$0.28"]
    assert_consecutive_lines(text, [
        "Konten A (1 units)", "Total Revenues", "$1.00", "PayPal Fee 5.00%", "-$0.05",
        "Creator Split 30.00%", "$0.29", "Product Total", "$0.29",
        "Konten B (1 units)", "Total Revenues", "$1.00", "PayPal Fee 5.00%", "-$0.05",
        "Creator Split 30.00%", "$0.28", "Product Total", "$0.28",
        "Subtotal: $0.57",
        "Total: $0.57",
    ])
    for label in ("Total Revenues", "PayPal Fee", "Creator Split", "Product Total"):
        assert text.count(label) == 2, label
    assert_no_internal_money(text)


def test_payout_slip_without_paypal_fee_skips_fee_row(client, admin_headers, outbox):
    assert client.put("/settings", json={"paypal_fee_pct": 0, "idr_rate": 16500}, headers=admin_headers).status_code == 200
    creator_id = seed_creator(method="bank", details=BANK)
    post_payout(client, admin_headers, creator_id)
    _, text = sent_slip(outbox)
    # Fee 0: net = net80 = 80, × 30% = 24.
    assert_consecutive_lines(text, [
        "Royal Mansion (10 units)", "Total Revenues", "$80.00",
        "Creator Split 30.00%", "$24.00",
        "Product Total", "$24.00",
    ])
    assert "PayPal Fee" not in text


def test_payout_slip_keeps_fee_snapshot(client, admin_headers, outbox):
    creator_id = seed_creator(method="bank", details=BANK)
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    # Fee diubah setelah payout dicatat: slip yang dibuat ulang tetap memakai 5%.
    client.put("/settings", json={"paypal_fee_pct": 10, "idr_rate": 17000}, headers=admin_headers)
    text = regenerate_slip(payout_id)
    assert_consecutive_lines(text, ["PayPal Fee 5.00%", "-$4.00", "Creator Split 30.00%", "$22.80"])
    assert "Exchange Rate: Rp16.500,00/$" in text


def test_payout_slip_item_without_calculation_chain(client, admin_headers, outbox):
    # Item yang dicatat sebelum net80_usd/net_usd ada: hanya Product Total.
    creator_id = seed_creator(method="bank", details=BANK)
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    with SessionLocal() as db:
        for item in db.get(models.Payout, payout_id).items:
            item.net80_usd = item.net_usd = None
        db.commit()
    text = regenerate_slip(payout_id)
    assert_consecutive_lines(text, ["Royal Mansion (10 units)", "Product Total", "$22.80", "Subtotal: $22.80"])
    for absent in ("Total Revenues", "PayPal Fee", "Creator Split"):
        assert absent not in text, absent


def test_payout_slip_paypal_has_no_rupiah(client, admin_headers, outbox):
    creator_id = seed_creator(method="paypal", details={"paypal_email": "kreator@gmail.com"})
    post_payout(client, admin_headers, creator_id)
    _, text = sent_slip(outbox)
    assert "Total: $22.80" in text
    for absent in ("Rp", "Exchange Rate", "Total (IDR)", "Note", "kreator@gmail.com", "kr***"):
        assert absent not in text, absent
    assert_no_internal_money(text)
    assert_no_at_sign_outside_emails(text)


def test_payout_slip_for_legacy_payout_and_account_without_username(client, admin_headers, outbox):
    creator_id = seed_creator(method="bank", details=BANK, username=None)
    with SessionLocal() as db:
        payout_id = add_payout(db, db.get(models.User, creator_id), 5.0).id
        db.commit()
    # Payout lama: slip dibuat saat kirim ulang email.
    assert client.post(f"/payouts/{payout_id}/notify", headers=admin_headers).status_code == 200

    filename, text = sent_slip(outbox)
    # Tanpa username: nama; tanpa periode: tanggal bayar.
    assert filename == "Payout Slip - Kreator - 1 November 2026.pdf"
    assert "Revenue Month: -" in text
    assert "No per-content breakdown is available for this payout." in text
    assert "Total: $5.00" in text
    # Baris "<username> - Squareclouds Studio" dilewati: nama langsung diikuti email.
    assert_consecutive_lines(text, ["Kreator", "creator@example.com"])
    assert_no_at_sign_outside_emails(text)


def test_payout_slip_uses_company_address_setting(client, admin_headers, outbox):
    body = {"paypal_fee_pct": 5, "idr_rate": 16500, "company_address": "Jalan Baru No. 7, Medan, Sumatera Utara 20111"}
    assert client.put("/settings", json=body, headers=admin_headers).status_code == 200
    creator_id = seed_creator(method="bank", details=BANK)
    post_payout(client, admin_headers, creator_id)

    _, text = sent_slip(outbox)
    # Satu baris dengan koma: dipecah per koma.
    assert_consecutive_lines(text, [
        "contact@squarecloudsmc.com", "Jalan Baru No. 7", "Medan", "Sumatera Utara 20111"
    ])
    assert "Jalan Halat" not in text


def test_slip_address_lines():
    import main

    assert main.slip_address_lines("A\nB\nC") == ["A", "B", "C"]
    assert main.slip_address_lines("  A  \n\n B ") == ["A", "B"]
    # Satu baris: dipecah per koma; baris yang sudah dipisah tidak dipecah lagi.
    assert main.slip_address_lines("Jl. A No. 1, Medan, Sumut 20111") == ["Jl. A No. 1", "Medan", "Sumut 20111"]
    assert main.slip_address_lines("Jl. A, Gg. B\nMedan") == ["Jl. A, Gg. B", "Medan"]
    # Maksimal 3 baris; sisanya digabung ke baris terakhir.
    assert main.slip_address_lines("A, B, C, D, E") == ["A", "B", "C, D, E"]
    assert main.slip_address_lines("") == []


def slip_data(block_count, **overrides):
    """block_count konten, masing-masing 4 baris (Total Revenues, fee, split, Product Total)."""
    items = [
        payout_slip.SlipItem(
            f"Konten {i:02d} ({i} units)",
            [("Total Revenues", f"${i}.00"), ("PayPal Fee 5.00%", "-$0.05"), ("Creator Split 30.00%", "$0.30")],
            "$0.30",
        )
        for i in range(1, block_count + 1)
    ]
    data = dict(
        title="Payout Slip - kreator - Oktober 2026", created_on="3 November 2026", revenue_month="Oktober 2026",
        sender=["Squareclouds Studio"], recipient=["Kreator"], items=items,
        total_usd="$1.00", exchange_rate="Rp16.500,00/$", total_idr="Rp16.500,00", note=None,
    )
    return payout_slip.SlipData(**{**data, **overrides})


def test_payout_pdf_fits_30_rows_on_first_page():
    # 7 konten × 4 baris = 28 baris tabel: satu halaman.
    pages = pdf_pages(payout_slip.render(slip_data(7)))
    assert "Konten 07 (7 units)" in pages[0]
    assert "Total: $1.00" in pages[-1]


def test_payout_pdf_continues_after_30_rows_without_splitting_a_block():
    # 8 konten × 4 baris = 32 baris: konten ke-8 utuh di halaman 2.
    pages = pdf_pages(payout_slip.render(slip_data(8, note="Catatan panjang")))
    assert len(pages) == 2
    assert "Konten 07 (7 units)" in pages[0]
    assert "Konten 08" not in pages[0]
    assert "Total:" not in pages[0]
    assert_consecutive_lines(pages[1], [
        "Content", "Comment", "Price",
        "Konten 08 (8 units)", "Total Revenues", "$8.00",
        "PayPal Fee 5.00%", "-$0.05", "Creator Split 30.00%", "$0.30", "Product Total", "$0.30",
    ])
    for part in ("Subtotal: $1.00", "Total: $1.00", "Total (IDR): Rp16.500,00", "Note: Catatan panjang"):
        assert part in pages[1], part


def test_slip_chunks_keep_blocks_whole():
    def block(rows):
        return payout_slip.SlipItem("x", [("a", "b")] * (rows - 1), "y")

    sizes = [[len(c) for c in payout_slip._chunks(items)] for items in (
        [block(4)] * 8,     # 7 × 4 = 28 ≤ 30, sisa 1
        [block(3)] * 10,    # tanpa baris fee: 10 × 3 = 30 pas
        [block(3)] * 11,
        [],
    )]
    assert sizes == [[7, 1], [10], [10, 1], [0]]


# ============================================================================
# ARSIP GOOGLE DRIVE
# ============================================================================

@pytest.fixture
def drive(monkeypatch, outbox):
    """Ganti gdrive.upload_pdf/delete_file. fail / fail_delete = True membuat
    panggilan berikutnya melempar error."""
    state = {"uploads": [], "deleted": [], "fail": False, "fail_delete": False}

    def fake_upload(filename, data, subfolder):
        if state["fail"]:
            raise RuntimeError("Drive mati")
        # Jumlah email yang sudah terkirim saat upload (urutan: email dulu).
        state["uploads"].append({"filename": filename, "data": data, "subfolder": subfolder, "emails": len(outbox)})
        return f"drive-file-{len(state['uploads'])}"

    def fake_delete(file_id):
        state["deleted"].append(file_id)
        if state["fail_delete"]:
            raise RuntimeError("Drive mati")

    monkeypatch.setattr(gdrive, "upload_pdf", fake_upload)
    monkeypatch.setattr(gdrive, "delete_file", fake_delete)
    return state


def get_drive_file_id(payout_id):
    with SessionLocal() as db:
        return db.get(models.Payout, payout_id).drive_file_id


def test_payout_slip_uploaded_to_drive_after_email(client, admin_headers, outbox, drive):
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["drive_saved"] is True
    assert "Slip tersimpan di Google Drive." in body["message"]
    assert body["data"]["drive_file_id"] == "drive-file-1"
    assert get_drive_file_id(body["data"]["id"]) == "drive-file-1"

    [upload] = drive["uploads"]
    assert upload["filename"] == "Payout Slip - kreator - Oktober 2026.pdf"
    assert upload["subfolder"] == "2026-10"
    assert upload["emails"] == 1  # email dikirim lebih dulu
    # PDF yang sama dengan lampiran email.
    [(_, attached, _)] = outbox[-1]["attachments"]
    assert upload["data"] == attached


def test_payout_saved_when_drive_upload_fails(client, admin_headers, outbox, drive):
    drive["fail"] = True
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["drive_saved"] is False
    assert body["notified"] is True
    assert "gagal disimpan ke Google Drive" in body["message"]
    assert body["data"]["drive_file_id"] is None
    with SessionLocal() as db:
        payout = db.get(models.Payout, body["data"]["id"])
        assert (payout.amount_usd, payout.drive_file_id) == (22.8, None)


def test_payout_saved_when_drive_not_configured(client, admin_headers):
    # conftest mengosongkan GDRIVE_*: upload dilewati tanpa menghubungi Google.
    creator_id = seed_creator(method="bank", details=BANK)
    res = post_payout(client, admin_headers, creator_id)
    assert res.status_code == 201, res.text
    assert res.json()["drive_saved"] is False
    assert get_drive_file_id(res.json()["data"]["id"]) is None
    with pytest.raises(gdrive.DriveNotConfigured):
        gdrive.upload_pdf("x.pdf", b"%PDF", "2026-10")


def test_reupload_payout_slip_to_drive(client, admin_headers, drive):
    drive["fail"] = True
    creator_id = seed_creator(method="bank", details=BANK)
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    url = f"/payouts/{payout_id}/drive"

    # Admin-only.
    assert client.post(url).status_code == 401
    assert client.post(url, headers=login(client)).status_code == 403
    assert client.post("/payouts/999/drive", headers=admin_headers).status_code == 404

    # Masih gagal -> 502, drive_file_id tetap NULL.
    res = client.post(url, headers=admin_headers)
    assert res.status_code == 502
    assert get_drive_file_id(payout_id) is None

    drive["fail"] = False
    res = client.post(url, headers=admin_headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["drive_file_id"] == "drive-file-1"
    assert get_drive_file_id(payout_id) == "drive-file-1"
    assert drive["uploads"][0]["filename"] == "Payout Slip - kreator - Oktober 2026.pdf"
    assert drive["uploads"][0]["data"].startswith(b"%PDF")

    # Sudah tersimpan -> tidak diupload dua kali.
    assert client.post(url, headers=admin_headers).status_code == 400
    assert len(drive["uploads"]) == 1


def test_reupload_legacy_payout_uses_payment_month_folder(client, admin_headers, drive):
    creator_id = seed_creator(method="bank", details=BANK)
    with SessionLocal() as db:
        payout_id = add_payout(db, db.get(models.User, creator_id), 5.0, paid_at="2026-09-15").id
        db.commit()
    assert client.post(f"/payouts/{payout_id}/drive", headers=admin_headers).status_code == 200
    [upload] = drive["uploads"]
    assert (upload["filename"], upload["subfolder"]) == ("Payout Slip - kreator - 15 September 2026.pdf", "2026-09")


def test_delete_payout_deletes_drive_file(client, admin_headers, drive):
    creator_id = seed_creator(method="bank", details=BANK, sales=SEPT_OCT_NOV)
    september = post_payout(client, admin_headers, creator_id, "2026-09").json()["data"]["id"]
    october = post_payout(client, admin_headers, creator_id, "2026-10").json()["data"]["id"]

    assert client.delete(f"/payouts/{september}", headers=admin_headers).status_code == 200
    assert drive["deleted"] == ["drive-file-1"]

    # Error Drive diabaikan: payout tetap terhapus.
    drive["fail_delete"] = True
    assert client.delete(f"/payouts/{october}", headers=admin_headers).status_code == 200
    assert drive["deleted"] == ["drive-file-1", "drive-file-2"]
    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 0


def test_delete_payout_without_drive_file_skips_drive(client, admin_headers, drive):
    drive["fail"] = True
    creator_id = seed_creator(method="bank", details=BANK)
    payout_id = post_payout(client, admin_headers, creator_id).json()["data"]["id"]
    assert client.delete(f"/payouts/{payout_id}", headers=admin_headers).status_code == 200
    assert drive["deleted"] == []


class FakeDriveRequest:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeDriveFiles:
    """Tiruan service.files() Drive API v3 yang mencatat semua panggilan."""

    def __init__(self, folders):
        self.folders = dict(folders)  # nama subfolder -> ID
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        name = re.search(r"name = '([^']+)'", kwargs["q"]).group(1)
        found = [{"id": self.folders[name]}] if name in self.folders else []
        return FakeDriveRequest({"files": found})

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        body = kwargs["body"]
        if body.get("mimeType") == gdrive.FOLDER_MIME:
            self.folders[body["name"]] = f"folder-{body['name']}"
            return FakeDriveRequest({"id": self.folders[body["name"]]})
        return FakeDriveRequest({"id": "pdf-file-id"})

    def delete(self, **kwargs):
        self.calls.append(("delete", kwargs))
        return FakeDriveRequest({})


class FakeDriveService:
    def __init__(self, files):
        self._files = files

    def files(self):
        return self._files


def test_gdrive_creates_month_subfolder_once_and_uses_all_drives(monkeypatch):
    monkeypatch.setenv("GDRIVE_SA_FILE", "sa.json")
    monkeypatch.setenv("GDRIVE_FOLDER_ID", "root-folder")
    files = FakeDriveFiles({"2026-07": "folder-juli"})
    monkeypatch.setattr(gdrive, "_service", lambda sa_file: FakeDriveService(files))

    assert gdrive.upload_pdf("Payout Slip - a - Agustus 2026.pdf", b"%PDF-1", "2026-08") == "pdf-file-id"
    assert gdrive.upload_pdf("Payout Slip - b - Agustus 2026.pdf", b"%PDF-2", "2026-08") == "pdf-file-id"
    assert gdrive.upload_pdf("Payout Slip - c - Juli 2026.pdf", b"%PDF-3", "2026-07") == "pdf-file-id"

    # Subfolder 2026-08 dibuat sekali; 2026-07 sudah ada.
    folder_creates = [kw for op, kw in files.calls if op == "create" and kw["body"].get("mimeType") == gdrive.FOLDER_MIME]
    assert folder_creates == [{
        "body": {"name": "2026-08", "mimeType": gdrive.FOLDER_MIME, "parents": ["root-folder"]},
        "fields": "id",
        "supportsAllDrives": True,
    }]
    for op, kw in files.calls:
        assert kw["supportsAllDrives"] is True, op
        if op == "list":
            assert "'root-folder' in parents" in kw["q"]
            assert kw["includeItemsFromAllDrives"] is True
    file_creates = [kw for op, kw in files.calls if op == "create" and "media_body" in kw]
    assert [kw["body"]["parents"] for kw in file_creates] == [["folder-2026-08"], ["folder-2026-08"], ["folder-juli"]]
    assert file_creates[0]["body"]["name"] == "Payout Slip - a - Agustus 2026.pdf"
    assert file_creates[0]["media_body"].mimetype() == "application/pdf"

    gdrive.delete_file("pdf-file-id")
    assert files.calls[-1] == ("delete", {"fileId": "pdf-file-id", "supportsAllDrives": True})
