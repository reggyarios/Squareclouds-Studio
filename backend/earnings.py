"""Rumus uang portal kreator. Satu-satunya tempat perhitungan pendapatan;
endpoint kreator dan admin sama-sama memakai modul ini.

Rantai uang (docs/payout-v2.2.md §0):

    gross          = harga × unit                      (Pathway: field `gross` per hari)
    net80          = gross × 80%                       (Pathway: field `creator` per hari)
    net            = net80 × (1 − paypal_fee_pct/100)  (fee PayPal saat Pathway membayar)
    bagian_kreator = net × split_pct/100               (split per konten)
    bagian_sq      = net − Σ bagian_kreator
    IDR            = USD × idr_rate                    (hanya payout non-PayPal)

Angka dihitung tanpa pembulatan; pembulatan ke 2 desimal hanya di output (`money`).
"""
import json
import math
from datetime import datetime, timezone

from sqlalchemy import and_, func, literal_column
from sqlalchemy.orm import Session

import models

# Bagian gross yang dibayar Pathway ke Squareclouds. Hanya untuk baris
# daily_sales lama yang gross_usd/net80_usd-nya masih NULL.
PATHWAY_NET_SHARE = 0.8

# Metode payout yang dibayar dalam rupiah (dikonversi dengan idr_rate).
IDR_METHODS = ("bank", "ewallet")


def money(value: float) -> float:
    """Bulatkan ke 2 desimal untuk output (+0.0 mengubah -0.0 jadi 0.0)."""
    return round(value, 2) + 0.0


def allocate_cents(values: list[float]) -> list[float]:
    """Bulatkan tiap nilai ke sen sehingga jumlahnya persis money(sum(values)).

    Membulatkan satu per satu bisa meleset sesen dari total yang dibulatkan
    (3 × 1/3 -> 0,33 × 3 = 0,99, padahal total 1,00). Metode sisa terbesar:
    semua dibulatkan ke bawah, lalu sen yang kurang diberikan ke nilai dengan
    sisa pecahan terbesar (seri: urutan input).
    """
    total_cents = round(money(sum(values)) * 100)
    scaled = [v * 100 for v in values]
    cents = [math.floor(s) for s in scaled]
    by_remainder = sorted(range(len(values)), key=lambda i: scaled[i] - cents[i], reverse=True)
    for i in by_remainder[: max(total_cents - sum(cents), 0)]:
        cents[i] += 1
    return [c / 100 for c in cents]


def net_from_net80(net80: float, fee_pct: float) -> float:
    return net80 * (1 - fee_pct / 100)


def creator_share(net: float, split_pct: float) -> float:
    return net * split_pct / 100


def to_idr(usd: float, rate: float) -> float:
    return usd * rate


def format_usd(value: float) -> str:
    """22.8 -> "$22.80" (sama dengan formatUsd di frontend)."""
    return f"${value:,.2f}"


def format_idr(value: float) -> str:
    """Rupiah format Indonesia, selalu 2 desimal: 2036925 -> "Rp2.036.925,00".

    Satu-satunya pemformat rupiah backend (email, pesan); sama dengan
    formatIDR di frontend/src/lib/portal.ts.
    """
    text = f"{abs(value):,.2f}"
    # Tanpa tanda minus kalau nilainya jadi 0,00 setelah dibulatkan.
    sign = "-" if value < 0 and text.strip("0.,") else ""
    return sign + "Rp" + text.replace(",", "_").replace(".", ",").replace("_", ".")


# ============================================================================
# SETTINGS
# ============================================================================

def get_setting_float(db: Session, key: str, default) -> float:
    row = db.get(models.Setting, key)
    try:
        return float(row.value) if row is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def set_setting(db: Session, key: str, value) -> None:
    """Simpan nilai setting tanpa commit; pemanggil yang commit."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row = db.get(models.Setting, key)
    if row is None:
        db.add(models.Setting(key=key, value=str(value), updated_at=now))
    else:
        row.value = str(value)
        row.updated_at = now


def paypal_fee_pct(db: Session) -> float:
    return get_setting_float(db, "paypal_fee_pct", models.SETTING_DEFAULTS["paypal_fee_pct"])


def idr_rate(db: Session) -> float:
    return get_setting_float(db, "idr_rate", models.SETTING_DEFAULTS["idr_rate"])


# ============================================================================
# PENJUALAN PER KONTEN
# ============================================================================

def content_rows(db: Session, user_id: int | None = None, month: str | None = None) -> list[dict]:
    """Penjualan per (konten, bulan): units, gross_usd, net80_usd, net_usd.

    user_id: hanya konten yang tertaut ke kreator itu. month (YYYY-MM): hanya
    bulan itu. Kolom yang masih NULL (baris belum disinkron ulang sejak kolom
    itu ada) memakai fallback harga konten × unit; 0 dari Pathway tetap 0.
    """
    sale = models.DailySales
    # literal_column supaya substr di SELECT dan GROUP BY identik; PostgreSQL
    # menolak kalau argumennya jadi bind parameter yang berbeda.
    month_col = func.substr(sale.date, literal_column("1"), literal_column("7"))
    fallback_gross = sale.quantity * models.Content.price

    query = (
        db.query(
            sale.content_id,
            month_col.label("month"),
            func.sum(sale.quantity),
            func.sum(func.coalesce(sale.gross_usd, fallback_gross)),
            func.sum(func.coalesce(sale.net80_usd, fallback_gross * PATHWAY_NET_SHARE)),
        )
        .join(models.Content, models.Content.id == sale.content_id)
        .group_by(sale.content_id, month_col)
    )
    if user_id is not None:
        query = query.join(
            models.CreatorSplit,
            and_(
                models.CreatorSplit.content_id == sale.content_id,
                models.CreatorSplit.user_id == user_id,
            ),
        )
    if month:
        query = query.filter(month_col == month)

    fee = paypal_fee_pct(db)
    return [
        {
            "content_id": content_id,
            "month": row_month,
            "units": int(units or 0),
            "gross_usd": float(gross or 0),
            "net80_usd": float(net80 or 0),
            "net_usd": net_from_net80(float(net80 or 0), fee),
        }
        for content_id, row_month, units, gross, net80 in query.all()
    ]


# ============================================================================
# KREATOR
# ============================================================================

def load_details(raw: str | None) -> dict | None:
    """JSON payout_details/details -> dict (None kalau kosong/rusak)."""
    try:
        value = json.loads(raw) if raw else None
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def serialize_payout(payout: models.Payout, include_internal: bool) -> dict:
    item = {
        "id": payout.id,
        "period_month": payout.period_month,
        "paid_at": payout.paid_at,
        "amount_usd": money(payout.amount_usd),
        "idr_rate": payout.idr_rate,
        "amount_idr": money(payout.amount_idr) if payout.amount_idr is not None else None,
        "method": payout.method,
        "note": payout.note,
    }
    if include_internal:
        item.update(
            details=load_details(payout.details),
            created_by=payout.created_by,
            created_at=payout.created_at,
            notified_at=payout.notified_at,
        )
    return item


def serialize_payout_items(payout: models.Payout, include_internal: bool) -> list[dict]:
    """Rincian per konten. split_pct hanya untuk admin (include_internal)."""
    result = []
    for row in payout.items:
        item = {
            "content_id": row.content_id,
            "name": row.content_name,
            "units": row.units,
            "share_usd": money(row.share_usd),
        }
        if include_internal:
            item["split_pct"] = row.split_pct
        result.append(item)
    return result


def creator_summary(db: Session, user: models.User, include_internal: bool) -> dict:
    """Pendapatan, pembayaran, dan saldo tertunda satu kreator (USD, plus
    perkiraan rupiah kalau metode payout-nya bank/e-wallet).

    include_internal=False (respons kreator) hanya berisi unit dan bagian
    kreator: tidak ada gross, net80, net, split %, maupun bagian Squareclouds.
    include_internal=True (hanya admin) menambahkan gross_usd, net_usd, dan
    split_pct.
    """
    rate = idr_rate(db)
    links = (
        db.query(models.CreatorSplit, models.Content)
        .join(models.Content, models.Content.id == models.CreatorSplit.content_id)
        .filter(models.CreatorSplit.user_id == user.id)
        .order_by(models.Content.name)
        .all()
    )

    # Konten tertaut tanpa penjualan tetap ditampilkan (unit 0).
    contents = {
        content.id: {
            "content": content,
            "split_pct": split.split_percentage,
            "units": 0, "share": 0.0, "gross": 0.0, "net": 0.0,
        }
        for split, content in links
    }
    months = {}
    for row in content_rows(db, user_id=user.id):
        bucket = contents[row["content_id"]]
        share = creator_share(row["net_usd"], bucket["split_pct"])
        month = months.setdefault(row["month"], {"units": 0, "share": 0.0, "gross": 0.0, "net": 0.0})
        for b in (bucket, month):
            b["units"] += row["units"]
            b["share"] += share
            b["gross"] += row["gross_usd"]
            b["net"] += row["net_usd"]

    # Field dipilih satu per satu (bukan disaring) supaya field internal tidak
    # pernah ikut ke respons kreator.
    by_content = []
    for content_id, b in contents.items():
        item = {
            "content_id": content_id,
            "name": b["content"].name,
            "status": b["content"].status,
            "units": b["units"],
            "share_usd": money(b["share"]),
        }
        if include_internal:
            item.update(gross_usd=money(b["gross"]), net_usd=money(b["net"]), split_pct=b["split_pct"])
        by_content.append(item)

    by_month = []
    for month, b in sorted(months.items(), reverse=True):
        item = {"month": month, "units": b["units"], "share_usd": money(b["share"])}
        if include_internal:
            item.update(gross_usd=money(b["gross"]), net_usd=money(b["net"]))
        by_month.append(item)

    payouts = (
        db.query(models.Payout)
        .filter(models.Payout.user_id == user.id)
        .order_by(models.Payout.paid_at.desc(), models.Payout.id.desc())
        .all()
    )
    earned = sum(b["share"] for b in contents.values())
    paid = sum(p.amount_usd for p in payouts)
    outstanding = earned - paid

    # Perkiraan rupiah dengan kurs saat ini, hanya untuk payout bank/e-wallet.
    # Rupiah yang benar-benar dibayar ada di amount_idr tiap payout.
    def approx_idr(usd: float) -> float | None:
        return money(to_idr(usd, rate)) if user.payout_method in IDR_METHODS else None

    return {
        "total_earned_usd": money(earned),
        "total_paid_usd": money(paid),
        "outstanding_usd": money(outstanding),
        "idr_rate": rate,
        "total_earned_idr": approx_idr(earned),
        "total_paid_idr": approx_idr(paid),
        "outstanding_idr": approx_idr(outstanding),
        "by_content": by_content,
        "by_month": by_month,
        "payouts": [serialize_payout(p, include_internal) for p in payouts],
    }


# ============================================================================
# PAYOUT PER BULAN
# ============================================================================

def shift_month(month: str, delta: int) -> str:
    """"2026-01", -1 -> "2025-12"."""
    index = int(month[:4]) * 12 + int(month[5:7]) - 1 + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def last_complete_month(db: Session) -> str | None:
    """Bulan sebelum bulan dari tanggal data terakhir di daily_sales
    (2026-11-05 -> "2026-10"); None kalau belum ada data.

    Diambil dari seluruh daily_sales, bukan hanya konten satu kreator: bot
    menyinkron semua konten sekaligus, jadi tanggal terakhir = sejauh mana data
    Pathway sudah masuk. Bulan dari tanggal itu masih berjalan, jadi belum
    bisa dibayar.
    """
    last_date = db.query(func.max(models.DailySales.date)).scalar()
    return shift_month(last_date[:7], -1) if last_date else None


def creator_months(db: Session, user: models.User) -> list[dict]:
    """Bulan-bulan yang bisa dibayar satu kreator, urut lama ke baru: dari
    bulan pertama dengan bagian > 0 sampai bulan lengkap terakhir (bulan di
    antaranya ikut, walau 0). Bulan berjalan tidak pernah ada di sini.

    share_usd = bagian kreator bulan itu (2 desimal) = jumlah yang dicatat
    POST /payouts. share_idr = share_usd × kurs saat ini, hanya untuk metode
    bank/e-wallet (None untuk PayPal/belum diisi); juga persis jumlah rupiah
    yang dicatat.

    items = rincian per konten yang terjual di bulan itu, urut nama:
    {content_id, name, units, share_usd}. Σ items.share_usd = share_usd persis
    (allocate_cents); disalin ke payout_items saat payout dicatat.
    """
    last_complete = last_complete_month(db)
    if last_complete is None:
        return []

    links = {
        content_id: (pct, name)
        for content_id, pct, name in (
            db.query(models.CreatorSplit.content_id, models.CreatorSplit.split_percentage, models.Content.name)
            .join(models.Content, models.Content.id == models.CreatorSplit.content_id)
            .filter(models.CreatorSplit.user_id == user.id)
        )
    }
    # {month: {content_id: {content_id, name, units, share}}}; content_rows
    # memberi satu baris per (konten, bulan).
    totals = {}
    for row in content_rows(db, user_id=user.id):
        if row["month"] > last_complete:
            continue
        pct, name = links[row["content_id"]]
        totals.setdefault(row["month"], {})[row["content_id"]] = {
            "content_id": row["content_id"],
            "name": name,
            "units": row["units"],
            "share": creator_share(row["net_usd"], pct),
        }

    def month_items(month: str) -> list[dict]:
        contents = sorted(totals.get(month, {}).values(), key=lambda c: (c["name"].lower(), c["content_id"]))
        amounts = allocate_cents([c["share"] for c in contents])
        return [
            {"content_id": c["content_id"], "name": c["name"], "units": c["units"], "share_usd": amount}
            for c, amount in zip(contents, amounts)
        ]

    earning = sorted(
        m for m, contents in totals.items() if money(sum(c["share"] for c in contents.values())) > 0
    )
    if not earning:
        return []

    paid = dict(
        db.query(models.Payout.period_month, models.Payout.id).filter(
            models.Payout.user_id == user.id,
            models.Payout.period_month.isnot(None),
        )
    )
    rate = idr_rate(db)
    result = []
    month = earning[0]
    while month <= last_complete:
        items = month_items(month)
        # Dari items (bukan money(Σ share) lagi) supaya total = Σ rincian persis.
        share_usd = money(sum(i["share_usd"] for i in items))
        result.append({
            "month": month,
            "units": sum(i["units"] for i in items),
            "share_usd": share_usd,
            "share_idr": money(to_idr(share_usd, rate)) if user.payout_method in IDR_METHODS else None,
            "paid": month in paid,
            "payout_id": paid.get(month),
            "items": items,
        })
        month = shift_month(month, 1)
    return result


# ============================================================================
# ADMIN
# ============================================================================

MONEY_KEYS = ("gross_usd", "net80_usd", "net_usd", "creators_share_usd", "squareclouds_share_usd")


def _empty_totals(**extra) -> dict:
    return {**extra, "units": 0, **{k: 0.0 for k in MONEY_KEYS}}


def _add_totals(bucket: dict, values: dict) -> None:
    bucket["units"] += values["units"]
    for k in MONEY_KEYS:
        bucket[k] += values[k]


def _output_totals(bucket: dict) -> dict:
    return {**bucket, **{k: money(bucket[k]) for k in MONEY_KEYS}}


def admin_overview(db: Session, month: str | None = None) -> dict:
    """Gross, net80, net, Σ bagian kreator, dan bagian Squareclouds: total,
    per konten (+ rincian kreator), dan per bulan (+ per konten di bulan itu).
    month (YYYY-MM) membatasi ke satu bulan.
    """
    content_info = {
        c.id: (c.name, c.status)
        for c in db.query(models.Content.id, models.Content.name, models.Content.status)
    }
    splits = {}
    for content_id, user_id, user_name, pct in (
        db.query(
            models.CreatorSplit.content_id,
            models.CreatorSplit.user_id,
            models.User.name,
            models.CreatorSplit.split_percentage,
        )
        .join(models.User, models.User.id == models.CreatorSplit.user_id)
        .order_by(models.User.name)
    ):
        splits.setdefault(content_id, []).append((user_id, user_name, pct))

    def content_bucket(buckets: dict, content_id: int) -> dict:
        if content_id not in buckets:
            name, status = content_info[content_id]
            buckets[content_id] = _empty_totals(
                content_id=content_id, name=name, status=status, creators={}
            )
        return buckets[content_id]

    totals = _empty_totals()
    contents = {}
    months = {}
    for row in content_rows(db, month=month):
        content_id = row["content_id"]
        shares = [
            (user_id, user_name, pct, creator_share(row["net_usd"], pct))
            for user_id, user_name, pct in splits.get(content_id, [])
        ]
        creators_total = sum(s[3] for s in shares)
        values = {
            "units": row["units"],
            "gross_usd": row["gross_usd"],
            "net80_usd": row["net80_usd"],
            "net_usd": row["net_usd"],
            "creators_share_usd": creators_total,
            "squareclouds_share_usd": row["net_usd"] - creators_total,
        }

        month_bucket = months.setdefault(
            row["month"], {"totals": _empty_totals(month=row["month"]), "contents": {}}
        )
        _add_totals(totals, values)
        _add_totals(month_bucket["totals"], values)
        for bucket in (content_bucket(contents, content_id), content_bucket(month_bucket["contents"], content_id)):
            _add_totals(bucket, values)
            for user_id, user_name, pct, share in shares:
                creator = bucket["creators"].setdefault(
                    user_id, {"user_id": user_id, "name": user_name, "split_pct": pct, "share_usd": 0.0}
                )
                creator["share_usd"] += share

    def output_content(bucket: dict) -> dict:
        creators = [{**c, "share_usd": money(c["share_usd"])} for c in bucket["creators"].values()]
        return {**_output_totals(bucket), "creators": creators}

    def output_contents(buckets: dict) -> list[dict]:
        return [output_content(b) for b in sorted(buckets.values(), key=lambda b: b["name"].lower())]

    return {
        "paypal_fee_pct": paypal_fee_pct(db),
        "totals": _output_totals(totals),
        "by_content": output_contents(contents),
        "by_month": [
            {**_output_totals(m["totals"]), "by_content": output_contents(m["contents"])}
            for _, m in sorted(months.items(), reverse=True)
        ],
    }
