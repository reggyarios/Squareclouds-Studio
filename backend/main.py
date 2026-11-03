from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from jose import JWTError, jwt
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import uuid
import io
import json
from PIL import Image

from database import create_tables, SessionLocal
import models
import schemas
import auth
from utils.file_storage import delete_upload, extract_upload_path


# ============================================================================
# APPLICATION / STORAGE
# ============================================================================

app = FastAPI(
    title="Squareclouds API",
    description="Portal Pendapatan Creator Minecraft & CMS Backend",
    root_path="/api",  # Tambahkan baris ini
)

PROJECT_ROOT = Path(__file__).resolve().parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.on_event("startup")
def on_startup():
    create_tables()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# SECURITY
# ============================================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kadaluarsa. Silakan login kembali.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM]
        )
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    # Admin selalu lolos; kreator hanya kalau sudah disetujui dan masih aktif.
    if user.role != "Admin" and user.account_status != "Active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun belum aktif. Silakan login kembali.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user):
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Akses ditolak.")


# Origin yang boleh memanggil API dari browser. Tambahkan lewat
# CORS_EXTRA_ORIGINS di .env (dipisah koma) kalau perlu, mis. untuk dev lokal.
ALLOWED_ORIGINS = [
    "https://squarecloudsmc.com",
    "https://www.squarecloudsmc.com",
    "https://access.squarecloudsmc.com",
    "https://creator.squarecloudsmc.com",
] + [o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# FILE HELPERS
# ============================================================================

def parse_gallery_urls(value: str | None) -> list[str]:
    if not value:
        return []

    value = value.strip()
    if not value:
        return []

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
    except (json.JSONDecodeError, TypeError):
        pass

    return [item.strip() for item in value.split(",") if item.strip()]


def get_commission_files(item: models.CMSCommission) -> list[str]:
    return (
        ([item.thumbnail_url] if item.thumbnail_url else [])
        + parse_gallery_urls(item.gallery_urls)
    )


def get_cms_file_paths(item) -> list[str]:
    if isinstance(item, models.CMSCommission):
        return get_commission_files(item)

    attr = {
        models.CMSMarketplace: "image_url",
        models.CMSPremade: "image_url",
        models.CMSTeamMember: "image_url",
        models.CMSExhibition: "image_url",
        models.CMSClient: "img",
    }
    for model, field in attr.items():
        if isinstance(item, model):
            value = getattr(item, field)
            return [value] if value else []
    return []


def get_all_database_upload_references(db: Session) -> set[str]:
    references = set()

    # Select only the fields that can contain upload references instead of
    # loading complete ORM objects.
    queries = (
        db.query(models.CMSCommission.thumbnail_url, models.CMSCommission.gallery_urls),
        db.query(models.CMSMarketplace.image_url),
        db.query(models.CMSPremade.image_url),
        db.query(models.CMSTeamMember.image_url),
        db.query(models.CMSExhibition.image_url),
        db.query(models.CMSClient.img),
    )

    for rows in queries:
        for row in rows:
            for value in row:
                if value is None:
                    continue
                values = parse_gallery_urls(value) if isinstance(value, str) and value.startswith("[") else [value]
                for path in values:
                    normalized = extract_upload_path(path)
                    if normalized:
                        references.add(normalized)

    return references


def delete_files_if_unreferenced(
    db: Session, file_paths: list[str | None]
) -> int:
    if not file_paths:
        return 0

    references = get_all_database_upload_references(db)
    deleted = 0
    processed = set()

    for file_path in file_paths:
        normalized = extract_upload_path(file_path)
        if not normalized or normalized in processed or normalized in references:
            continue

        processed.add(normalized)
        try:
            if delete_upload(file_path):
                deleted += 1
        except ValueError as e:
            print(f"[FILE DELETE] Invalid path: {e}")
        except Exception as e:
            print(f"[FILE DELETE] Failed to delete {file_path}: {e}")

    return deleted


# ============================================================================
# HOME / IMAGE UPLOAD / LOGIN
# ============================================================================

@app.get("/")
def home():
    return {"status": "Online", "message": "Backend Squareclouds siap dan aman!"}


@app.post("/upload-image/")
async def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Akses ditolak!")

    try:
        # PIL can read the uploaded stream directly; this avoids creating an
        # additional full-size bytes object with await file.read().
        image = Image.open(file.file)
        filename = f"{uuid.uuid4().hex}.webp"
        image.save(UPLOADS_DIR / filename, format="webp", quality=85)

        base_url = os.getenv("BASE_URL", "https://api.squarecloudsmc.com")
        return {"url": f"{base_url}/api/uploads/{filename}"}
    except Exception as e:
        print(f"Error Upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses gambar: {str(e)}",
        )
    finally:
        await file.close()


@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.email == form_data.username)
        .first()
    )

    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Email atau password salah")

    if user.role != "Admin" and user.account_status != "Active":
        raise HTTPException(
            status_code=403,
            detail=(
                "Akun dinonaktifkan."
                if user.account_status == "Inactive"
                else "Akun belum disetujui admin."
            ),
        )

    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
    }


# ============================================================================
# REGISTER
# ============================================================================

JOB_TITLES = ("Builder", "Skin Artist", "Developer", "Keyart Artist", "Other")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MIN_PASSWORD_LENGTH = 8


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    name = payload.name.strip()
    email = payload.email.strip()
    job_title = payload.job_title.strip()

    if not name or not email or not payload.password or not job_title:
        raise HTTPException(
            status_code=400,
            detail="Nama, email, password, dan job title wajib diisi.",
        )
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=400, detail="Format email tidak valid.")
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password minimal {MIN_PASSWORD_LENGTH} karakter.",
        )
    if job_title not in JOB_TITLES:
        raise HTTPException(status_code=400, detail="Job title tidak valid.")

    if (
        db.query(models.User.id)
        .filter(func.lower(models.User.email) == email.lower())
        .first()
    ):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar!")

    try:
        db.add(
            models.User(
                name=name,
                email=email,
                role="Creator",
                job_title=job_title,
                password=auth.get_password_hash(payload.password),
                account_status="Pending",
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email sudah terdaftar!")

    return {"message": "Pendaftaran diterima. Tunggu persetujuan admin."}


# ============================================================================
# USERS (ADMIN)
# ============================================================================

USER_STATUS_ORDER = {"Pending": 0, "Active": 1, "Inactive": 2}


def serialize_user(u) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "job_title": u.job_title,
        "account_status": u.account_status,
        "created_at": u.created_at,
    }


def get_creator_or_error(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kreator tidak ditemukan")
    # 400, bukan 403: frontend menganggap 401/403 sebagai sesi berakhir.
    if user.role == "Admin":
        raise HTTPException(
            status_code=400,
            detail="Akun Admin tidak bisa diubah dari sini.",
        )
    return user


@app.get("/users/")
def get_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    users = (
        db.query(
            models.User.id,
            models.User.name,
            models.User.email,
            models.User.role,
            models.User.job_title,
            models.User.account_status,
            models.User.created_at,
        )
        .filter(models.User.role == "Creator")
        .all()
    )

    # Pending dulu, lalu yang terbaru mendaftar. Akun lama tanpa created_at
    # ditaruh paling bawah di kelompoknya.
    users.sort(key=lambda u: u.created_at or "", reverse=True)
    users.sort(key=lambda u: USER_STATUS_ORDER.get(u.account_status, 9))

    return {"data": [serialize_user(u) for u in users]}


@app.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: schemas.UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    user = get_creator_or_error(db, user_id)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Nama tidak boleh kosong.")
        user.name = name

    if payload.job_title is not None:
        if payload.job_title not in JOB_TITLES:
            raise HTTPException(status_code=400, detail="Job title tidak valid.")
        user.job_title = payload.job_title

    if payload.account_status is not None:
        if payload.account_status not in ("Active", "Inactive"):
            raise HTTPException(
                status_code=400,
                detail="Status akun hanya boleh Active atau Inactive.",
            )
        user.account_status = payload.account_status

    if payload.password:
        if len(payload.password) < MIN_PASSWORD_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Password minimal {MIN_PASSWORD_LENGTH} karakter.",
            )
        user.password = auth.get_password_hash(payload.password)

    db.commit()
    db.refresh(user)
    return {"message": "Data kreator diperbarui.", "data": serialize_user(user)}


@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    user = get_creator_or_error(db, user_id)

    db.query(models.CreatorSplit).filter(
        models.CreatorSplit.user_id == user_id
    ).delete()
    db.delete(user)
    db.commit()

    return {"message": "Kreator berhasil dihapus permanen!"}


# ============================================================================
# CONTENTS (READ-ONLY, DIISI pathway_bot.py) & SPLITS
# ============================================================================

MAX_CREATOR_SPLIT_TOTAL = 80.0


def serialize_contents(db: Session, content_id: int | None = None) -> list[dict]:
    query = db.query(models.Content)
    split_query = db.query(models.CreatorSplit, models.User.name).join(
        models.User, models.User.id == models.CreatorSplit.user_id
    )
    units_query = db.query(
        models.DailySales.content_id,
        func.coalesce(func.sum(models.DailySales.quantity), 0),
    )
    if content_id is not None:
        query = query.filter(models.Content.id == content_id)
        split_query = split_query.filter(models.CreatorSplit.content_id == content_id)
        units_query = units_query.filter(models.DailySales.content_id == content_id)

    units_by_content = dict(units_query.group_by(models.DailySales.content_id).all())

    splits_by_content = {}
    for split, user_name in split_query.all():
        splits_by_content.setdefault(split.content_id, []).append(
            {
                "user_id": split.user_id,
                "user_name": user_name,
                "split_percentage": split.split_percentage,
            }
        )

    return [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "pack_type": c.pack_type,
            "world_type": c.world_type,
            "tier": c.tier,
            "price": c.price,
            "release_date": c.release_date,
            "pathway_status": c.pathway_status,
            "pathway_product_id": c.pathway_product_id,
            "pathway_offer_id": c.pathway_offer_id,
            "last_synced_at": c.last_synced_at,
            "units_total": int(units_by_content.get(c.id, 0) or 0),
            "splits": splits_by_content.get(c.id, []),
        }
        for c in query.order_by(models.Content.name).all()
    ]


@app.get("/contents/")
def get_contents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return {"data": serialize_contents(db)}


@app.put("/contents/{content_id}/splits")
def replace_content_splits(
    content_id: int,
    payload: schemas.SplitsReplace,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    content = db.query(models.Content).filter(models.Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content tidak ditemukan")

    user_ids = [s.user_id for s in payload.splits]
    if len(user_ids) != len(set(user_ids)):
        raise HTTPException(status_code=400, detail="Kreator tidak boleh duplikat.")

    if any(s.split_percentage <= 0 for s in payload.splits):
        raise HTTPException(
            status_code=400,
            detail="Persentase split tiap kreator harus lebih dari 0.",
        )

    total = sum(s.split_percentage for s in payload.splits)
    if round(total, 6) > MAX_CREATOR_SPLIT_TOTAL:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Total split kreator maksimal {MAX_CREATOR_SPLIT_TOTAL:g}% "
                f"(sekarang {total:g}%)."
            ),
        )

    if user_ids:
        active_ids = {
            uid
            for (uid,) in db.query(models.User.id).filter(
                models.User.id.in_(user_ids),
                models.User.role == "Creator",
                models.User.account_status == "Active",
            )
        }
        invalid = [uid for uid in user_ids if uid not in active_ids]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Split hanya untuk kreator berstatus Active. "
                    f"User ID tidak valid: {', '.join(map(str, invalid))}."
                ),
            )

    try:
        db.query(models.CreatorSplit).filter(
            models.CreatorSplit.content_id == content_id
        ).delete()
        db.add_all(
            models.CreatorSplit(
                user_id=s.user_id,
                content_id=content_id,
                split_percentage=s.split_percentage,
            )
            for s in payload.splits
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Replace Splits Error: {e}")
        raise HTTPException(status_code=500, detail="Gagal menyimpan split.")

    return {
        "message": "Split konten diperbarui.",
        "data": serialize_contents(db, content_id)[0],
    }


# ============================================================================
# ADMIN REPORTS
# ============================================================================

@app.get("/admin-reports/")
def get_admin_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)

    # One query replaces the DailySales -> Content N+1 query pattern.
    rows = (
        db.query(models.DailySales, models.Content)
        .join(models.Content, models.Content.id == models.DailySales.content_id)
        .all()
    )

    grouped = {}
    for sale, content in rows:
        month = sale.date[:7]
        key = (month, content.id)
        value = grouped.setdefault(
            key,
            {
                "bulan": month,
                "content_name": content.name,
                "qty": 0,
                "gross": 0.0,
                "content_id": content.id,
            },
        )
        value["qty"] += sale.quantity
        value["gross"] += sale.quantity * content.price

    content_ids = {v["content_id"] for v in grouped.values()}
    split_rows = (
        db.query(models.CreatorSplit, models.User)
        .join(models.User, models.User.id == models.CreatorSplit.user_id)
        .filter(models.CreatorSplit.content_id.in_(content_ids))
        .all()
        if content_ids
        else []
    )

    splits_by_content = {}
    for split, creator in split_rows:
        splits_by_content.setdefault(split.content_id, []).append(
            (creator.name, split.split_percentage)
        )

    result = []
    for value in grouped.values():
        gross = value["gross"]
        result.append(
            {
                "bulan": value["bulan"],
                "nama_konten": value["content_name"],
                "total_qty": value["qty"],
                "gross": gross,
                "sq_revenue": gross * 0.20,
                "creator_breakdown": [
                    f"{name} ({percentage}%): "
                    f"${gross * (percentage / 100):.2f}"
                    for name, percentage in splits_by_content.get(
                        value["content_id"], []
                    )
                ],
            }
        )

    return {"data": sorted(result, key=lambda x: x["bulan"], reverse=True)}


# ============================================================================
# CREATOR DASHBOARD
# ============================================================================

@app.get("/creator-dashboard/")
def get_creator_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "Creator":
        raise HTTPException(status_code=403)

    proyek_aktif = []
    grafik_harian = []
    monthly_summary = {}
    total_saldo = 0.0

    # One joined query replaces the nested split -> content -> sales queries.
    rows = (
        db.query(models.CreatorSplit, models.Content, models.DailySales)
        .join(
            models.Content,
            models.Content.id == models.CreatorSplit.content_id,
        )
        .join(
            models.DailySales,
            models.DailySales.content_id == models.Content.id,
        )
        .filter(models.CreatorSplit.user_id == current_user.id)
        .all()
    )

    # Preserve projects even when a content has no sales.
    projects = (
        db.query(models.CreatorSplit, models.Content)
        .join(models.Content, models.Content.id == models.CreatorSplit.content_id)
        .filter(models.CreatorSplit.user_id == current_user.id)
        .all()
    )
    proyek_aktif = [
        {
            "name": content.name,
            "status": content.status,
            "pack_type": content.pack_type,
            "release_date": content.release_date,
            "tier": content.tier,
        }
        for _, content in projects
    ]

    for split, content, record in rows:
        earned = (
            record.quantity
            * content.price
            * (split.split_percentage / 100)
        )
        total_saldo += earned

        grafik_harian.append(
            {
                "date": record.date,
                "content_name": content.name,
                "quantity": record.quantity,
            }
        )

        key = (record.date[:7], content.name)
        summary = monthly_summary.setdefault(
            key,
            {
                "month": record.date[:7],
                "content_name": content.name,
                "qty": 0,
                "earned": 0.0,
            },
        )
        summary["qty"] += record.quantity
        summary["earned"] += earned

    return {
        "nama": current_user.name,
        "job_title": current_user.job_title,
        "total_saldo": total_saldo,
        "proyek": proyek_aktif,
        "grafik_harian": grafik_harian,
        "riwayat_bulanan": sorted(
            monthly_summary.values(),
            key=lambda x: x["month"],
            reverse=True,
        ),
    }


# ============================================================================
# CMS GENERIC HELPERS
# ============================================================================

def cms_create(
    model,
    payload,
    db: Session,
    message: str,
):
    db.add(model(**payload.model_dump()))
    db.commit()
    return {"message": message}


def cms_get(model, db: Session):
    return {"data": db.query(model).all()}


def cms_update(
    model,
    item_id: int,
    payload,
    db: Session,
    not_found: str,
    message: str,
    image_field: str | None = None,
):
    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=not_found)

    old_image = getattr(item, image_field) if image_field else None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.commit()

    if image_field and old_image and old_image != getattr(item, image_field):
        delete_files_if_unreferenced(db, [old_image])

    return {"message": message}


def cms_delete(
    model,
    item_id: int,
    db: Session,
    not_found: str,
    message: str,
    file_getter=get_cms_file_paths,
):
    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=not_found)

    files = file_getter(item)
    db.delete(item)
    db.commit()
    delete_files_if_unreferenced(db, files)

    return {"message": message}


# ============================================================================
# CMS - COMMISSIONS
# ============================================================================

@app.get("/cms/commissions")
def get_commissions(db: Session = Depends(get_db)):
    return cms_get(models.CMSCommission, db)


@app.post("/cms/commissions")
def create_commission(
    payload: schemas.CMSCommissionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_create(
        models.CMSCommission,
        payload,
        db,
        "Project Commission ditambahkan!",
    )


@app.put("/cms/commissions/{item_id}")
def update_commission(
    item_id: int,
    payload: schemas.CMSCommissionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)

    item = db.query(models.CMSCommission).filter(
        models.CMSCommission.id == item_id
    ).first()
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Project Commission tidak ditemukan",
        )

    old_files = get_commission_files(item)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()

    new_files = get_commission_files(item)
    delete_files_if_unreferenced(
        db, [path for path in old_files if path not in new_files]
    )
    return {"message": "Project Commission diperbarui!"}


@app.delete("/cms/commissions/{item_id}")
def delete_commission(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_delete(
        models.CMSCommission,
        item_id,
        db,
        "Project Commission tidak ditemukan",
        "Project dihapus!",
    )


# ============================================================================
# CMS - MARKETPLACE
# ============================================================================

@app.get("/cms/marketplaces")
def get_marketplaces(db: Session = Depends(get_db)):
    return cms_get(models.CMSMarketplace, db)


@app.post("/cms/marketplaces")
def create_marketplace(
    payload: schemas.CMSMarketplaceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_create(
        models.CMSMarketplace,
        payload,
        db,
        "Item Marketplace ditambahkan!",
    )


@app.put("/cms/marketplaces/{item_id}")
def update_marketplace(
    item_id: int,
    payload: schemas.CMSMarketplaceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_update(
        models.CMSMarketplace,
        item_id,
        payload,
        db,
        "Marketplace item tidak ditemukan",
        "Item diperbarui!",
        "image_url",
    )


@app.delete("/cms/marketplaces/{item_id}")
def delete_marketplace(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_delete(
        models.CMSMarketplace,
        item_id,
        db,
        "Marketplace item tidak ditemukan",
        "Item dihapus!",
    )


# ============================================================================
# CMS - PREMADE
# ============================================================================

@app.get("/cms/premades")
def get_premades(db: Session = Depends(get_db)):
    return cms_get(models.CMSPremade, db)


@app.post("/cms/premades")
def create_premade(
    payload: schemas.CMSPremadeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_create(
        models.CMSPremade,
        payload,
        db,
        "Premade Asset ditambahkan!",
    )


@app.put("/cms/premades/{item_id}")
def update_premade(
    item_id: int,
    payload: schemas.CMSPremadeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_update(
        models.CMSPremade,
        item_id,
        payload,
        db,
        "Premade item tidak ditemukan",
        "Asset diperbarui!",
        "image_url",
    )


@app.delete("/cms/premades/{item_id}")
def delete_premade(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_delete(
        models.CMSPremade,
        item_id,
        db,
        "Premade item tidak ditemukan",
        "Asset dihapus!",
    )


# ============================================================================
# CMS - EXHIBITIONS
# ============================================================================

@app.get("/cms/exhibitions")
def get_exhibitions(db: Session = Depends(get_db)):
    return cms_get(models.CMSExhibition, db)


@app.post("/cms/exhibitions")
def create_exhibition(
    payload: schemas.CMSExhibitionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_create(
        models.CMSExhibition,
        payload,
        db,
        "Pameran ditambahkan!",
    )


@app.put("/cms/exhibitions/{item_id}")
def update_exhibition(
    item_id: int,
    payload: schemas.CMSExhibitionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_update(
        models.CMSExhibition,
        item_id,
        payload,
        db,
        "Pameran tidak ditemukan",
        "Pameran diperbarui!",
        "image_url",
    )


@app.delete("/cms/exhibitions/{item_id}")
def delete_exhibition(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_delete(
        models.CMSExhibition,
        item_id,
        db,
        "Pameran tidak ditemukan",
        "Pameran dihapus!",
    )


# ============================================================================
# CMS - TEAM
# ============================================================================

@app.get("/cms/team")
def get_team(db: Session = Depends(get_db)):
    return cms_get(models.CMSTeamMember, db)


@app.post("/cms/team")
def create_team(
    payload: schemas.CMSTeamCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_create(
        models.CMSTeamMember,
        payload,
        db,
        "Tim ditambahkan!",
    )


@app.put("/cms/team/{item_id}")
def update_team(
    item_id: int,
    payload: schemas.CMSTeamUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_update(
        models.CMSTeamMember,
        item_id,
        payload,
        db,
        "Team member tidak ditemukan",
        "Tim diperbarui!",
        "image_url",
    )


@app.delete("/cms/team/{item_id}")
def delete_team(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_delete(
        models.CMSTeamMember,
        item_id,
        db,
        "Team member tidak ditemukan",
        "Tim dihapus!",
    )


# ============================================================================
# CMS - CLIENTS
# ============================================================================

@app.get("/cms/clients")
def get_clients(db: Session = Depends(get_db)):
    return cms_get(models.CMSClient, db)


@app.post("/cms/clients")
def create_client(
    payload: schemas.CMSClientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)

    client = models.CMSClient(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)

    return {"message": "Client berhasil ditambahkan!", "data": client}


@app.put("/cms/clients/{item_id}")
def update_client(
    item_id: int,
    payload: schemas.CMSClientUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_update(
        models.CMSClient,
        item_id,
        payload,
        db,
        "Client tidak ditemukan.",
        "Client berhasil diperbarui!",
        "img",
    )


@app.delete("/cms/clients/{item_id}")
def delete_client(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return cms_delete(
        models.CMSClient,
        item_id,
        db,
        "Client tidak ditemukan",
        "Client dihapus!",
    )
