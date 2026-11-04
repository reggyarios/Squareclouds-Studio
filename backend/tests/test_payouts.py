"""Pendapatan kreator, payout, dan pengaturan (docs/payout-v2.2.md)."""
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
        add_content(db, splits=[(creator, 30)], sales=[("2026-09-01", 6000, 0, 0), ("2026-09-02", 396, 0, 0)])

        [row] = earnings.content_rows(db)
        assert row["gross_usd"] == pytest.approx(4797.0)
        assert row["net80_usd"] == pytest.approx(3837.6)
        assert row["net_usd"] == pytest.approx(3645.72)
        assert earnings.creator_summary(db, creator, include_internal=False)["total_earned_usd"] == 1093.72


def test_pathway_amounts_win_over_price(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        # Harga konten 0,75 tapi Pathway melaporkan gross 1,00 (mis. diskon/kurs).
        add_content(db, splits=[(creator, 50)], sales=[("2026-10-01", 1, 1.0, 0.8), ("2026-10-02", 2, 0, 0)])
        [row] = earnings.content_rows(db)
        assert row["gross_usd"] == pytest.approx(1.0 + 2 * 0.75)
        assert row["net80_usd"] == pytest.approx(0.8 + 2 * 0.75 * 0.8)


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


def test_outstanding_idr_only_for_rupiah_methods(client):
    with SessionLocal() as db:
        creator = add_creator(db)
        add_content(db, splits=[(creator, 30)], sales=[("2026-10-05", 10, 100.0, 80.0)])

        assert earnings.creator_summary(db, creator, False)["outstanding_idr"] is None
        creator.payout_method = "paypal"
        assert earnings.creator_summary(db, creator, False)["outstanding_idr"] is None
        creator.payout_method = "bank"
        assert earnings.creator_summary(db, creator, False)["outstanding_idr"] == 376200.0  # 22,8 × 16.500


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
