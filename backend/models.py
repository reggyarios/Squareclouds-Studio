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

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    role = Column(String, nullable=False)

    job_title = Column(String, nullable=True)

    password = Column(String, nullable=False)

    wallet_balance = Column(
        Float,
        default=0.0,
        nullable=False,
    )

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