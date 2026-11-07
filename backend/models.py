from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from database import Base


# ============================================================
# USER / CREATOR
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False, index=True)

    # 3-20 karakter [a-z0-9_], disimpan lowercase. Nullable untuk akun lama
    # yang dibuat sebelum ada username; akun itu tetap login pakai email.
    username = Column(
        String,
        unique=True,
        nullable=True,
        index=True,
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    role = Column(String, nullable=False)

    job_title = Column(String, nullable=True)

    password = Column(String, nullable=False)

    # Tidak dipakai lagi sejak payout v2.2 (saldo dihitung di earnings.py).
    # Kolom dibiarkan ada; jangan ditulis/dibaca.
    wallet_balance = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    # paypal | bank | ewallet (NULL = belum diisi kreator)
    payout_method = Column(String, nullable=True)

    # JSON, isinya tergantung payout_method:
    #   paypal  {"paypal_email"}
    #   bank    {"bank_name", "account_number", "account_name"}
    #   ewallet {"provider", "phone", "account_name"}
    payout_details = Column(String, nullable=True)

    # Pending | Active | Inactive. Kreator baru mendaftar sebagai Pending dan
    # baru bisa login setelah disetujui admin.
    account_status = Column(
        String,
        nullable=False,
        default="Pending",
        server_default="Pending",
    )

    # ISO timestamp UTC saat daftar
    created_at = Column(String, nullable=True)

    # Relationships
    splits = relationship(
        "CreatorSplit",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    history = relationship(
        "EarningHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# ============================================================
# INVITATION
# ============================================================

class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)

    # Disimpan lowercase
    email = Column(String, nullable=False, index=True)

    # secrets.token_urlsafe(32)
    token = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    invited_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    # ISO timestamp UTC
    created_at = Column(String, nullable=False)

    # created_at + 7 hari
    expires_at = Column(String, nullable=False)

    # Diisi saat kreator selesai mendaftar
    used_at = Column(String, nullable=True)


# ============================================================
# CONTENT
# ============================================================

class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    price = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    status = Column(
        String,
        default="Aktif",
        nullable=False,
    )

    content_type = Column(
        String,
        nullable=True,
    )

    # ---- Data dari Pathway (diisi otomatis oleh pathway_bot.py) ----
    # productID dari halaman Sales. Kunci utama pencocokan konten.
    pathway_product_id = Column(String, unique=True, nullable=True, index=True)
    # ID offer dari URL /dashboard/offers/<id> (kalau tersedia).
    pathway_offer_id = Column(String, unique=True, nullable=True, index=True)
    # Status mentah di tab Offers: In Development / Review / Submissions /
    # Pending Release / Published.
    pathway_status = Column(String, nullable=True)
    # "World", "Skin Pack", "World + Skin Pack", ...
    pack_type = Column(String, nullable=True)
    # "Survival Spawn", ... (hanya untuk World)
    world_type = Column(String, nullable=True)
    # Royalty tier (1..19)
    tier = Column(Integer, nullable=True)
    # YYYY-MM-DD
    release_date = Column(String, nullable=True)
    # ISO timestamp sinkronisasi terakhir
    last_synced_at = Column(String, nullable=True)

    # Relationships
    splits = relationship(
        "CreatorSplit",
        back_populates="content",
        cascade="all, delete-orphan",
    )

    daily_sales = relationship(
        "DailySales",
        back_populates="content",
        cascade="all, delete-orphan",
    )

    sales_transactions = relationship(
        "SalesTransaction",
        back_populates="content",
        cascade="all, delete-orphan",
    )


# ============================================================
# CREATOR SPLIT
# ============================================================

class CreatorSplit(Base):
    __tablename__ = "creator_splits"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=False,
        index=True,
    )

    split_percentage = Column(
        Float,
        nullable=False,
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="splits",
    )

    content = relationship(
        "Content",
        back_populates="splits",
    )

    # Prevent duplicate creator/content split
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "content_id",
            name="uq_creator_content_split",
        ),
    )


# ============================================================
# EARNING HISTORY
# ============================================================

# Tidak dipakai lagi sejak payout v2.2 (diganti tabel payouts). Tabel
# dibiarkan ada; jangan ditulis/dibaca.
class EarningHistory(Base):
    __tablename__ = "earning_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    content_name = Column(
        String,
        nullable=False,
    )

    amount = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    # Format: YYYY-MM
    report_month = Column(
        String,
        nullable=False,
        index=True,
    )

    # Relationship
    user = relationship(
        "User",
        back_populates="history",
    )


# ============================================================
# SALES TRANSACTION
# ============================================================

class SalesTransaction(Base):
    __tablename__ = "sales_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Format: YYYY-MM
    report_month = Column(
        String,
        nullable=False,
        index=True,
    )

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=False,
        index=True,
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=0,
    )

    gross_revenue = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    squareclouds_revenue = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    # Relationship
    content = relationship(
        "Content",
        back_populates="sales_transactions",
    )


# ============================================================
# DAILY SALES
# ============================================================

class DailySales(Base):
    __tablename__ = "daily_sales"

    id = Column(Integer, primary_key=True, index=True)

    # Format: YYYY-MM-DD
    date = Column(
        String,
        nullable=False,
        index=True,
    )

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=False,
        index=True,
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Dari Pathway per hari: field `gross` (harga × unit) dan field `creator`
    # (80% gross, yang diterima Squareclouds dari Pathway). NULL = baris lama
    # yang belum disinkron ulang; hanya itu yang memakai fallback harga di
    # earnings.py. 0 dari Pathway berarti memang $0.
    gross_usd = Column(Float, nullable=True)

    net80_usd = Column(Float, nullable=True)

    # Relationship
    content = relationship(
        "Content",
        back_populates="daily_sales",
    )

    # One sales record per content per day
    __table_args__ = (
        UniqueConstraint(
            "date",
            "content_id",
            name="uq_daily_sales_content_date",
        ),
    )


# ============================================================
# SETTINGS
# ============================================================

# Nilai awal (di-seed scripts/migrate_payouts.py, juga fallback di
# earnings.py kalau barisnya belum ada).
SETTING_DEFAULTS = {
    "paypal_fee_pct": "5",   # fee PayPal saat Pathway membayar Squareclouds
    "idr_rate": "16500",     # kurs Rp per USD untuk payout non-PayPal
    # Alamat pengirim di slip payout PDF, satu baris per baris alamat.
    "company_address": (
        "Jalan Halat, Gang Merdeka No.12\n"
        "Kecamatan Medan Area, Kota Medan\n"
        "Sumatera Utara 20216"
    ),
}


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)

    value = Column(String, nullable=False)

    # ISO timestamp UTC
    updated_at = Column(String, nullable=True)


# ============================================================
# PAYOUT
# ============================================================

class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Bulan pendapatan yang dibayar (YYYY-MM); amount_usd = bagian kreator di
    # bulan itu. NULL = payout lama sebelum payout per bulan (tanpa periode).
    period_month = Column(String, nullable=True)

    amount_usd = Column(Float, nullable=False)

    # Snapshot kurs saat dibayar
    idr_rate = Column(Float, nullable=True)

    # Hanya untuk payout non-PayPal
    amount_idr = Column(Float, nullable=True)

    # paypal | bank | ewallet, snapshot saat dibayar
    method = Column(String, nullable=False)

    # JSON snapshot users.payout_details saat dibayar
    details = Column(String, nullable=False)

    note = Column(String, nullable=True)

    # YYYY-MM-DD
    paid_at = Column(String, nullable=False)

    # Admin yang mencatat
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    # ISO timestamp UTC
    created_at = Column(String, nullable=False)

    # ISO timestamp UTC saat email notifikasi payout terkirim (NULL = gagal /
    # belum terkirim; admin bisa kirim ulang)
    notified_at = Column(String, nullable=True)

    # Rincian per konten (snapshot saat dicatat). Payout lama tidak punya.
    # passive_deletes: baris item dihapus ON DELETE CASCADE di database.
    items = relationship(
        "PayoutItem",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PayoutItem.id",
    )

    # Satu payout per kreator per bulan. NULL tidak bentrok (payout lama).
    # Index (bukan UniqueConstraint) supaya create_all dan
    # scripts/migrate_payouts.py membuat objek yang sama dengan nama yang sama.
    __table_args__ = (
        Index("uq_payouts_user_period", "user_id", "period_month", unique=True),
    )


class PayoutItem(Base):
    """Rincian satu payout per konten, disalin dari earnings.creator_months
    saat payout dicatat. Σ share_usd = payouts.amount_usd (persis, per sen)."""

    __tablename__ = "payout_items"

    id = Column(Integer, primary_key=True, index=True)

    payout_id = Column(
        Integer,
        ForeignKey("payouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content_id = Column(
        Integer,
        ForeignKey("contents.id"),
        nullable=False,
    )

    # Snapshot saat dibayar (nama konten bisa berubah lewat sinkron Pathway)
    content_name = Column(String, nullable=False)

    units = Column(Integer, nullable=False)

    share_usd = Column(Float, nullable=False)

    # Snapshot split kreator saat dibayar. Internal: tidak pernah dikirim ke kreator.
    split_pct = Column(Float, nullable=False)


# ============================================================
# CMS — COMMISSION
# ============================================================

class CMSCommission(Base):
    __tablename__ = "cms_commissions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String,
        nullable=True,
    )

    description = Column(
        String,
        nullable=True,
    )

    thumbnail_url = Column(
        String,
        nullable=True,
    )

    # Example: "2024"
    year = Column(
        String,
        default="2024",
        nullable=False,
        index=True,
    )

    # Stored as a string.
    # Frontend can store JSON array here.
    # Example:
    # ["image1.webp", "image2.webp"]
    gallery_urls = Column(
        String,
        default="",
        nullable=False,
    )

    link = Column(
        String,
        nullable=True,
    )


# ============================================================
# CMS — MARKETPLACE
# ============================================================

class CMSMarketplace(Base):
    __tablename__ = "cms_marketplace"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    content_type = Column(
        String,
        nullable=False,
    )

    image_url = Column(
        String,
        nullable=True,
    )

    price_minecoin = Column(
        Integer,
        default=0,
        nullable=False,
    )

    link = Column(
        String,
        nullable=True,
    )


# ============================================================
# CMS — PREMADE
# ============================================================

class CMSPremade(Base):
    __tablename__ = "cms_premade"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    category = Column(
        String,
        default="Worlds",
        nullable=False,
        index=True,
    )

    description = Column(
        String,
        nullable=True,
    )

    image_url = Column(
        String,
        nullable=True,
    )

    price_usd = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    link = Column(
        String,
        nullable=True,
    )


# ============================================================
# CMS — TEAM MEMBERS
# ============================================================

class CMSTeamMember(Base):
    __tablename__ = "cms_team_members"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    role = Column(
        String,
        nullable=False,
    )

    image_url = Column(
        String,
        nullable=True,
    )

    bio = Column(
        String,
        nullable=True,
    )

    link_x = Column(
        String,
        nullable=True,
    )

    link_linkedin = Column(
        String,
        nullable=True,
    )

    link_instagram = Column(
        String,
        nullable=True,
    )

    link_website = Column(
        String,
        nullable=True,
    )


# ============================================================
# CMS — EXHIBITIONS
# ============================================================

class CMSExhibition(Base):
    __tablename__ = "cms_exhibitions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    image_url = Column(
        String,
        nullable=False,
    )

    link = Column(
        String,
        nullable=True,
    )


# ============================================================
# CMS — CLIENTS
# ============================================================

class CMSClient(Base):
    __tablename__ = "cms_client"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # URL/path logo client
    img = Column(
        String,
        nullable=False,
    )

    # Destination URL
    link = Column(
        String,
        nullable=True,
    )