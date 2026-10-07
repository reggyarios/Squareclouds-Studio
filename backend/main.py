from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt
from typing import Dict, List
from pathlib import Path
import math
import os
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
    return user


def require_admin(user):
    if user.role != "Admin":
        raise HTTPException(status_code=403, detail="Akses ditolak.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

        base_url = os.getenv("BASE_URL", "https://squarecloudsmc.com")
        return {"url": f"{base_url}/uploads/{filename}"}
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
# USERS
# ============================================================================

@app.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email sudah terdaftar!")

    try:
        db.add(
            models.User(
                name=user.name,
                email=user.email,
                role=user.role,
                job_title=user.job_title,
                password=auth.get_password_hash(user.password),
            )
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Create User Error: {e}")
        raise HTTPException(status_code=500, detail="Gagal membuat user.")

    return {"message": "User berhasil dibuat!"}


@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    users = db.query(
        models.User.id,
        models.User.name,
        models.User.email,
        models.User.role,
        models.User.job_title,
    ).all()

    return {
        "data": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "job_title": u.job_title,
            }
            for u in users
        ]
    }


@app.put("/users/{user_id}")
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kreator tidak ditemukan")

    for field in ("name", "email", "job_title"):
        value = getattr(user_update, field)
        if value:
            setattr(user, field, value)

    if user_update.password:
        user.password = auth.get_password_hash(user_update.password)

    db.commit()
    return {"message": "Data Kreator berhasil diperbarui!"}


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kreator tidak ditemukan")

    db.query(models.CreatorSplit).filter(
        models.CreatorSplit.user_id == user_id
    ).delete()
    db.delete(user)
    db.commit()

    return {"message": "Kreator berhasil dihapus permanen!"}


# ============================================================================
# CONTENTS
# ============================================================================

@app.post("/contents/")
def create_content(content: schemas.ContentCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Content)
        .filter(func.lower(models.Content.name) == content.name.lower())
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Nama konten sudah terdaftar!")

    try:
        db.add(
            models.Content(
                name=content.name,
                price=content.price,
                status=content.status,
                content_type=content.content_type,
            )
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Create Content Error: {e}")
        raise HTTPException(status_code=500, detail="Gagal membuat konten.")

    return {"message": "Konten berhasil ditambahkan!"}


@app.get("/contents/")
def get_contents(db: Session = Depends(get_db)):
    contents = db.query(models.Content).all()
    splits = db.query(models.CreatorSplit).all()

    # O(1) lookup per content instead of one DB query for every content.
    splits_by_content = {}
    for s in splits:
        splits_by_content.setdefault(s.content_id, []).append(s)

    return {
        "data": [
            {
                "id": c.id,
                "name": c.name,
                "price": c.price,
                "status": c.status,
                "content_type": c.content_type,
                "splits": [
                    {"user_id": s.user_id, "percentage": s.split_percentage}
                    for s in splits_by_content.get(c.id, [])
                ],
            }
            for c in contents
        ]
    }


@app.post("/splits/")
def create_split(split: schemas.SplitCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.CreatorSplit)
        .filter(
            models.CreatorSplit.user_id == split.user_id,
            models.CreatorSplit.content_id == split.content_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Creator split untuk konten ini sudah ada.",
        )

    if split.split_percentage <= 0 or split.split_percentage > 100:
        raise HTTPException(
            status_code=400,
            detail="Persentase split harus antara 0 dan 100.",
        )

    try:
        db.add(
            models.CreatorSplit(
                user_id=split.user_id,
                content_id=split.content_id,
                split_percentage=split.split_percentage,
            )
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Create Split Error: {e}")
        raise HTTPException(status_code=500, detail="Gagal mengatur creator split.")

    return {"message": "Split royalti berhasil diatur!"}


@app.put("/contents/{content_id}")
def update_content(
    content_id: int,
    content_update: schemas.ContentUpdate,
    db: Session = Depends(get_db),
):
    content = db.query(models.Content).filter(models.Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content tidak ditemukan")

    for field in ("name", "status", "content_type"):
        value = getattr(content_update, field)
        if value:
            setattr(content, field, value)

    if content_update.price is not None:
        content.price = content_update.price

    if content_update.splits is not None:
        db.query(models.CreatorSplit).filter(
            models.CreatorSplit.content_id == content_id
        ).delete()

        db.add_all(
            models.CreatorSplit(
                user_id=s.user_id,
                content_id=content_id,
                split_percentage=s.percentage,
            )
            for s in content_update.splits
            if s.user_id and s.percentage > 0
        )

    db.commit()
    return {"message": "Data Konten & Split diperbarui!"}


@app.delete("/contents/{content_id}")
def delete_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(models.Content).filter(models.Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content tidak ditemukan")

    db.query(models.CreatorSplit).filter(
        models.CreatorSplit.content_id == content_id
    ).delete()
    db.query(models.DailySales).filter(
        models.DailySales.content_id == content_id
    ).delete()
    db.delete(content)
    db.commit()

    return {"message": "Konten dihapus permanen!"}


# ============================================================================
# PATHWAY SYNC
# ============================================================================

@app.post("/sync-pathway-daily/")
def sync_pathway_daily(
    payload: List[Dict],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    synced_count = 0

    try:
        # Cache content by lowercase name. This removes repeated SELECTs when
        # Pathway sends several records for the same content.
        content_cache = {
            name.lower(): content
            for name, content in (
                db.query(models.Content.name, models.Content)
                .all()
            )
        }

        # Cache existing sales by (date, content_id).
        sales_cache = {
            (sale.date, sale.content_id): sale
            for sale in db.query(models.DailySales).all()
        }

        for item in payload:
            content_name = item.get("productName")
            raw_units = int(item.get("totalUnits", 0))
            date_val = item.get("date")

            if not content_name or raw_units == 0 or not date_val:
                continue

            adjusted_units = math.floor(raw_units * 0.5)
            if adjusted_units <= 0:
                continue

            key = content_name.lower()
            content = content_cache.get(key)

            if not content:
                content = models.Content(
                    name=content_name,
                    price=0.0,
                    status="Development",
                    content_type="Other",
                )
                db.add(content)
                db.flush()
                content_cache[key] = content

            sale_key = (date_val, content.id)
            existing = sales_cache.get(sale_key)

            if existing:
                existing.quantity = adjusted_units
            else:
                existing = models.DailySales(
                    date=date_val,
                    content_id=content.id,
                    quantity=adjusted_units,
                )
                db.add(existing)
                sales_cache[sale_key] = existing

            synced_count += 1

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Pathway Sync Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Sync gagal. Tidak ada perubahan yang disimpan.",
        )

    return {"message": "Sync Berhasil!", "synced_count": synced_count}


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
        {"name": content.name, "status": content.status}
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
