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
"""
import json

import pytest

import auth
import earnings
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


def add_payout(db, user, amount_usd, paid_at="2026-11-01"):
    db.add(
        models.Payout(
            user_id=user.id,
            amount_usd=amount_usd,
            method="paypal",
            details="{}",
            paid_at=paid_at,
            created_at="2026-11-01T00:00:00+00:00",
        )
    )
    db.flush()


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


# ============================================================================
# ENDPOINT ADMIN
# ============================================================================

BANK = {"bank_name": "BCA", "account_number": "1234567890", "account_name": "Kreator Satu"}


def login(client, email="creator@example.com"):
    res = client.post("/login", data={"username": email, "password": CREATOR_PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def seed_creator(method=None, details=None):
    """Kreator Active dengan satu konten: gross 100, net80 80 -> share 30% = 22,8."""
    with SessionLocal() as db:
        creator = add_creator(
            db,
            payout_method=method,
            payout_details=None if details is None else json.dumps(details),
        )
        add_content(db, splits=[(creator, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])
        db.commit()
        return creator.id


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
    payout_id = client.post("/payouts", json={"user_id": creator_id, "amount_usd": 1}, headers=admin_headers).json()["data"]["id"]
    headers = login(client)

    assert client.get("/settings", headers=headers).status_code == 403
    assert client.put("/settings", json={"paypal_fee_pct": 0, "idr_rate": 1}, headers=headers).status_code == 403
    assert client.get(f"/users/{creator_id}/earnings", headers=headers).status_code == 403
    assert client.post("/payouts", json={"user_id": creator_id, "amount_usd": 1}, headers=headers).status_code == 403
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

    with SessionLocal() as db:
        admin_id = db.query(models.User.id).filter(models.User.role == "Admin").scalar()
    assert client.get(f"/users/{admin_id}/earnings", headers=admin_headers).status_code == 400
    assert client.get("/users/999/earnings", headers=admin_headers).status_code == 404


def test_create_payout_snapshots_method_and_reduces_outstanding(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    body = {"user_id": creator_id, "amount_usd": 10.004, "note": "  Oktober  ", "paid_at": "2026-11-03"}
    res = client.post("/payouts", json=body, headers=admin_headers)
    assert res.status_code == 201, res.text
    payout = res.json()["data"]
    assert payout["amount_usd"] == 10.0
    assert payout["idr_rate"] == 16500.0
    assert payout["amount_idr"] == 165000.0
    assert payout["method"] == "bank"
    assert payout["details"] == BANK
    assert payout["note"] == "Oktober"
    assert payout["paid_at"] == "2026-11-03"

    # Kreator ganti metode setelahnya: snapshot di payout lama tidak berubah.
    paypal = {"payout_method": "paypal", "payout_details": {"paypal_email": "k@pp.com"}}
    assert client.put("/me/payout", json=paypal, headers=login(client)).status_code == 200
    data = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()
    assert data["total_paid_usd"] == 10.0
    assert data["outstanding_usd"] == 12.8
    assert data["outstanding_idr"] is None
    assert data["payouts"][0]["details"] == BANK

    # PayPal: tanpa amount_idr. Seluruh saldo (seperti yang tampil, 2 desimal) boleh dibayar.
    res = client.post("/payouts", json={"user_id": creator_id, "amount_usd": 12.8}, headers=admin_headers)
    assert res.status_code == 201, res.text
    assert res.json()["data"]["amount_idr"] is None
    assert res.json()["data"]["method"] == "paypal"
    assert client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()["outstanding_usd"] == 0.0


def test_create_payout_rejections(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)

    def post(body):
        return client.post("/payouts", json=body, headers=admin_headers)

    res = post({"user_id": creator_id, "amount_usd": 22.81})
    assert res.status_code == 400
    assert "melebihi saldo tertunda" in res.json()["detail"]
    for amount in (0, -1, 0.004):
        assert post({"user_id": creator_id, "amount_usd": amount}).status_code == 400, amount
    assert post({"user_id": creator_id, "amount_usd": 1, "paid_at": "03-11-2026"}).status_code == 400
    assert post({"user_id": 999, "amount_usd": 1}).status_code == 404

    with SessionLocal() as db:
        no_method = add_creator(db, "nomethod@example.com")
        add_content(db, "Konten Lain", splits=[(no_method, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])
        inactive = add_creator(
            db, "inactive@example.com", payout_method="bank", payout_details=json.dumps(BANK)
        )
        inactive.account_status = "Inactive"
        db.commit()
        no_method_id, inactive_id = no_method.id, inactive.id

    res = post({"user_id": no_method_id, "amount_usd": 1})
    assert res.status_code == 400
    assert res.json()["detail"] == "Kreator belum mengisi metode payout."
    assert post({"user_id": inactive_id, "amount_usd": 1}).status_code == 400

    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 0


def test_delete_payout_restores_outstanding(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    res = client.post("/payouts", json={"user_id": creator_id, "amount_usd": 5}, headers=admin_headers)
    payout_id = res.json()["data"]["id"]
    assert client.delete(f"/payouts/{payout_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/payouts/{payout_id}", headers=admin_headers).status_code == 404
    assert client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()["outstanding_usd"] == 22.8


def test_delete_creator_also_deletes_payouts(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    client.post("/payouts", json={"user_id": creator_id, "amount_usd": 5}, headers=admin_headers)
    assert client.delete(f"/users/{creator_id}", headers=admin_headers).status_code == 200
    with SessionLocal() as db:
        assert db.query(models.Payout).count() == 0


def test_admin_reports_and_contents_use_overview(client, admin_headers):
    seed_creator()
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
    creator_id = seed_creator(method="bank", details=BANK)
    client.post("/payouts", json={"user_id": creator_id, "amount_usd": 5, "note": "x"}, headers=admin_headers)

    data = client.get("/creator-dashboard/", headers=login(client)).json()
    leaked = [k for k in all_keys(data) if any(part in k.lower() for part in FORBIDDEN_KEY_PARTS)]
    assert leaked == []
    assert data["total_earned_usd"] == 22.8
    assert data["total_paid_usd"] == 5.0
    assert data["outstanding_usd"] == 17.8
    assert data["outstanding_idr"] == 293700.0  # 17,8 × 16.500
    assert data["by_content"][0]["units"] == 10
    assert data["by_month"] == [{"month": "2026-10", "units": 10, "share_usd": 22.8}]
    assert data["payouts"][0]["note"] == "x"
    assert data["grafik_harian"] == [{"date": "2026-10-05", "content_name": "Royal Mansion", "quantity": 10}]
    assert client.get("/creator-dashboard/", headers=admin_headers).status_code == 403


def test_creator_payout_history_hides_snapshot_and_admin_fields(client, admin_headers):
    creator_id = seed_creator(method="bank", details=BANK)
    client.post("/payouts", json={"user_id": creator_id, "amount_usd": 5}, headers=admin_headers)

    [payout] = client.get("/creator-dashboard/", headers=login(client)).json()["payouts"]
    assert set(payout) == {"id", "paid_at", "amount_usd", "idr_rate", "amount_idr", "method", "note"}
    assert BANK["account_number"] not in str(payout)


def test_payout_idr_snapshot_survives_rate_change(client, admin_headers):
    creator_id = seed_creator(method="ewallet", details={"provider": "OVO", "phone": "081234567890", "account_name": "K"})
    client.post("/payouts", json={"user_id": creator_id, "amount_usd": 10}, headers=admin_headers)
    client.put("/settings", json={"paypal_fee_pct": 5, "idr_rate": 17000}, headers=admin_headers)

    data = client.get(f"/users/{creator_id}/earnings", headers=admin_headers).json()
    assert (data["payouts"][0]["idr_rate"], data["payouts"][0]["amount_idr"]) == (16500.0, 165000.0)
    assert data["idr_rate"] == 17000.0
    assert data["outstanding_idr"] == 217600.0  # 12,8 × 17.000


def test_settings_reject_non_numeric(client, admin_headers):
    body = {"paypal_fee_pct": "lima", "idr_rate": 16500}
    assert client.put("/settings", json=body, headers=admin_headers).status_code == 422
    assert client.get("/settings", headers=admin_headers).json()["paypal_fee_pct"] == 5.0
