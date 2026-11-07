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
import json
import smtplib

import pytest
from sqlalchemy.exc import IntegrityError

import auth
import earnings
import mailer
import models
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
        add_content(db, splits=[(creator, 30)], sales=[
            ("2026-06-10", 3, 0.0, 0.0),      # unit tanpa pendapatan: belum awal rentang
            ("2026-07-05", 10, 100.0, 80.0),  # 22,8
            # Agustus kosong: tetap ada (0) karena di dalam rentang.
            ("2026-09-05", 5, 50.0, 40.0),    # 11,4
            ("2026-10-31", 1, 10.0, 8.0),     # 2,28
            ("2026-11-05", 10, 100.0, 80.0),  # bulan berjalan: tidak ditawarkan
        ])
        july = add_payout(db, creator, 22.8, period_month="2026-07")

        months = earnings.creator_months(db, creator)
        assert months == [
            {"month": "2026-07", "units": 10, "share_usd": 22.8, "share_idr": 376200.0, "paid": True, "payout_id": july.id},
            {"month": "2026-08", "units": 0, "share_usd": 0.0, "share_idr": 0.0, "paid": False, "payout_id": None},
            {"month": "2026-09", "units": 5, "share_usd": 11.4, "share_idr": 188100.0, "paid": False, "payout_id": None},
            {"month": "2026-10", "units": 1, "share_usd": 2.28, "share_idr": 37620.0, "paid": False, "payout_id": None},
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


def seed_creator(method=None, details=None, sales=(OCTOBER_SALE,), data_until="2026-11-05"):
    """Kreator Active dengan satu konten (split 30%); default share Oktober 2026 = 22,8.

    data_until: tanggal penjualan terakhir di daily_sales, lewat konten lain
    tanpa kreator. Default 5 November, jadi Oktober = bulan lengkap terakhir
    dan bisa dibayar. None = tanpa konten tambahan itu.
    """
    with SessionLocal() as db:
        creator = add_creator(
            db,
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


def test_settings_get_put_and_validation(client, admin_headers):
    assert client.get("/settings", headers=admin_headers).json() == {"paypal_fee_pct": 5.0, "idr_rate": 16500.0}

    res = client.put("/settings", json={"paypal_fee_pct": 3.5, "idr_rate": 16250.5}, headers=admin_headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"] == {"paypal_fee_pct": 3.5, "idr_rate": 16250.5}
    assert client.get("/settings", headers=admin_headers).json() == {"paypal_fee_pct": 3.5, "idr_rate": 16250.5}

    for body in (
        {"paypal_fee_pct": -0.1, "idr_rate": 16500},
        {"paypal_fee_pct": 100.1, "idr_rate": 16500},
        {"paypal_fee_pct": 5, "idr_rate": 0},
        {"paypal_fee_pct": 5, "idr_rate": -1},
    ):
        assert client.put("/settings", json=body, headers=admin_headers).status_code == 400, body
    assert client.put("/settings", json={"paypal_fee_pct": 5}, headers=admin_headers).status_code == 422
    assert client.get("/settings", headers=admin_headers).json() == {"paypal_fee_pct": 3.5, "idr_rate": 16250.5}

    # Batas 0 dan 100 boleh.
    for fee in (0, 100):
        body = {"paypal_fee_pct": fee, "idr_rate": 1}
        assert client.put("/settings", json=body, headers=admin_headers).status_code == 200
    assert client.get("/settings", headers=admin_headers).json() == {"paypal_fee_pct": 100.0, "idr_rate": 1.0}


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
    assert data["months"] == [
        {"month": "2026-10", "units": 10, "share_usd": 22.8, "share_idr": 376200.0, "paid": False, "payout_id": None}
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
    assert data["months"][1] == {
        "month": "2026-10", "units": 5, "share_usd": 11.4, "share_idr": 193800.0, "paid": False, "payout_id": None
    }


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


def failing_send_mail(to, subject, html, text):
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
    assert mail["subject"] == "Payout Squareclouds Studio: $22.80 telah dikirim"
    for part in (
        "Halo Kreator,",
        "Periode : Oktober 2026\n",
        "$22.80",
        "≈ Rp376.200,00 (kurs Rp16.500,00/$)",
        "Transfer bank BCA ****7890",
        "3 November 2026",
        "Payout <Oktober>",
        "https://portal.test/creator",
    ):
        assert part in mail["text"], part
    assert ">Periode</td>" in mail["html"]
    assert ">Oktober 2026</td>" in mail["html"]
    assert "Payout &lt;Oktober&gt;" in mail["html"]
    assert "https://portal.test/creator" in mail["html"]
    assert BANK["account_number"] not in mail["text"] + mail["html"]


def test_payout_email_for_paypal_and_ewallet(client, admin_headers, outbox):
    creator_id = seed_creator(method="paypal", details={"paypal_email": "kreator@gmail.com"}, sales=SEPT_OCT_NOV)
    res = post_payout(client, admin_headers, creator_id, "2026-09")
    assert res.status_code == 201, res.text
    assert outbox[-1]["subject"] == "Payout Squareclouds Studio: $22.80 telah dikirim"
    assert "Periode : September 2026" in outbox[-1]["text"]
    assert "PayPal kr***@gmail.com" in outbox[-1]["text"]
    assert "Rp" not in outbox[-1]["text"]
    assert "Catatan" not in outbox[-1]["text"]

    with SessionLocal() as db:
        creator = db.get(models.User, creator_id)
        creator.payout_method = "ewallet"
        creator.payout_details = json.dumps({"provider": "DANA", "phone": "081234565678", "account_name": "K"})
        db.commit()
    post_payout(client, admin_headers, creator_id, "2026-10")
    assert "Periode : Oktober 2026" in outbox[-1]["text"]
    assert "DANA ****5678" in outbox[-1]["text"]
    assert "≈ Rp188.100,00 (kurs Rp16.500,00/$)" in outbox[-1]["text"]  # 11,4 × 16.500


def test_payout_email_without_period_for_legacy_payout(client, admin_headers, outbox):
    creator_id = seed_creator(method="bank", details=BANK)
    with SessionLocal() as db:
        payout_id = add_payout(db, db.get(models.User, creator_id), 5.0).id
        db.commit()
    assert client.post(f"/payouts/{payout_id}/notify", headers=admin_headers).status_code == 200
    assert "Periode" not in outbox[-1]["text"] + outbox[-1]["html"]
    assert "Jumlah  : $5.00" in outbox[-1]["text"]


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
    monkeypatch.setattr(mailer, "send_mail", lambda to, subject, html, text: sent.append(subject) or True)
    res = client.post(url, headers=admin_headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["notified_at"] is not None
    assert sent == ["Payout Squareclouds Studio: $22.80 telah dikirim"]

    # Sudah terkirim -> tidak dikirim dua kali.
    assert client.post(url, headers=admin_headers).status_code == 400
    assert client.post("/payouts/999/notify", headers=admin_headers).status_code == 404
    assert len(sent) == 1
