from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from jose import JWTError, jwt
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
import math
import os
import re
import secrets
import uuid
import io
import json
from PIL import Image

from database import create_tables, SessionLocal
import models
import schemas
import auth
import earnings
import gdrive
import mailer
import payout_slip
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
    # Field `username` dari form OAuth2 boleh berisi email atau username.
    # Username tidak boleh mengandung "@", jadi keduanya tidak tertukar.
    # Email baru selalu disimpan lowercase; lower() di kolom juga mencocokkan
    # akun lama yang tersimpan dengan huruf besar.
    identifier = form_data.username.strip().lower()
    column = models.User.email if "@" in identifier else models.User.username
    user = (
        db.query(models.User)
        .filter(func.lower(column) == identifier)
        .first()
    )

    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Email/username atau password salah")

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
# INVITATIONS & REGISTER
# ============================================================================

JOB_TITLES = ("Builder", "Skin Artist", "Developer", "Keyart Artist", "Other")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
# Sama dengan USERNAME_PATTERN di frontend/src/lib/portal.ts.
USERNAME_RE = re.compile(r"[a-z0-9_]{3,20}")
MIN_PASSWORD_LENGTH = 8
INVITATION_VALID_DAYS = 7
DEFAULT_PORTAL_URL = "https://creator.squarecloudsmc.com"


def iso_utc(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def is_invitation_expired(invitation: models.Invitation) -> bool:
    return datetime.fromisoformat(invitation.expires_at) <= datetime.now(timezone.utc)


def email_registered(db: Session, email: str) -> bool:
    return (
        db.query(models.User.id)
        .filter(func.lower(models.User.email) == email)
        .first()
        is not None
    )


def username_taken(db: Session, username: str) -> bool:
    return (
        db.query(models.User.id)
        .filter(func.lower(models.User.username) == username)
        .first()
        is not None
    )


def get_valid_invitation(db: Session, token: str | None) -> models.Invitation:
    invitation = (
        db.query(models.Invitation).filter(models.Invitation.token == token).first()
        if token
        else None
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Undangan tidak ditemukan")
    if invitation.used_at:
        raise HTTPException(status_code=410, detail="Undangan sudah dipakai")
    if is_invitation_expired(invitation):
        raise HTTPException(status_code=410, detail="Undangan sudah kedaluwarsa")
    return invitation


def portal_url() -> str:
    return (os.getenv("PORTAL_URL", "").strip() or DEFAULT_PORTAL_URL).rstrip("/")


def send_invitation_email(email: str, token: str) -> bool:
    link = f"{portal_url()}/register?token={token}"
    text = (
        "Halo,\n\n"
        "Anda diundang bergabung ke Creator Portal Squareclouds Studio. "
        "Buka link berikut untuk membuat akun:\n\n"
        f"{link}\n\n"
        f"Link ini berlaku {INVITATION_VALID_DAYS} hari. Setelah mendaftar, "
        "akun Anda bisa dipakai begitu disetujui admin.\n\n"
        "Salam,\nSquareclouds Studio"
    )
    html = f"""\
<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937;line-height:1.6">
  <p>Halo,</p>
  <p>Anda diundang bergabung ke <b>Creator Portal Squareclouds Studio</b>.
     Klik tombol di bawah untuk membuat akun.</p>
  <p><a href="{escape(link)}" style="display:inline-block;padding:10px 20px;border-radius:8px;
     background:#2563eb;color:#ffffff;text-decoration:none;font-weight:bold">Buat akun</a></p>
  <p style="font-size:12px;color:#6b7280">Atau buka link ini: {escape(link)}</p>
  <p>Link ini berlaku {INVITATION_VALID_DAYS} hari. Setelah mendaftar,
     akun Anda bisa dipakai begitu disetujui admin.</p>
  <p>Salam,<br>Squareclouds Studio</p>
</div>"""
    return mailer.send_mail(email, "Undangan Creator Portal Squareclouds Studio", html, text)


@app.post("/invitations", status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: schemas.InvitationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    email = payload.email.strip().lower()

    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=400, detail="Format email tidak valid.")
    if email_registered(db, email):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar!")

    # Undangan lama yang belum dipakai (aktif maupun kedaluwarsa) diganti
    # yang baru, jadi tiap email hanya punya satu link yang berlaku.
    db.query(models.Invitation).filter(
        models.Invitation.email == email,
        models.Invitation.used_at.is_(None),
    ).delete(synchronize_session=False)

    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    db.add(
        models.Invitation(
            email=email,
            token=token,
            invited_by=current_user.id,
            created_at=iso_utc(now),
            expires_at=iso_utc(now + timedelta(days=INVITATION_VALID_DAYS)),
        )
    )
    db.commit()

    try:
        sent = send_invitation_email(email, token)
    except Exception as e:
        print(f"Invitation Mail Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Undangan tersimpan, tetapi email gagal dikirim. Coba Kirim ulang.",
        )

    return {
        "message": f"Undangan terkirim ke {email}." if sent else f"Undangan untuk {email} dibuat.",
        "sent": sent,
    }


@app.get("/invitations")
def get_invitations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    invitations = (
        db.query(models.Invitation)
        .filter(models.Invitation.used_at.is_(None))
        .order_by(models.Invitation.created_at.desc())
        .all()
    )
    # Token sengaja tidak dikembalikan: admin tidak boleh bisa mendaftarkan
    # (dan tahu password) akun kreator.
    return {
        "data": [
            {
                "id": i.id,
                "email": i.email,
                "created_at": i.created_at,
                "expires_at": i.expires_at,
                "expired": is_invitation_expired(i),
            }
            for i in invitations
        ]
    }


@app.delete("/invitations/{invitation_id}")
def delete_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    invitation = (
        db.query(models.Invitation)
        .filter(
            models.Invitation.id == invitation_id,
            models.Invitation.used_at.is_(None),
        )
        .first()
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Undangan tidak ditemukan")

    email = invitation.email
    db.delete(invitation)
    db.commit()
    return {"message": f"Undangan untuk {email} dibatalkan."}


@app.get("/register/{token}")
def check_invitation(token: str, db: Session = Depends(get_db)):
    return {"email": get_valid_invitation(db, token).email}


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    invitation = get_valid_invitation(db, payload.token)
    email = invitation.email.lower()
    username = payload.username.strip().lower()
    name = payload.name.strip()
    job_title = payload.job_title.strip()

    if not username or not name or not payload.password or not job_title:
        raise HTTPException(
            status_code=400,
            detail="Username, nama, password, dan job title wajib diisi.",
        )
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(
            status_code=400,
            detail="Username 3–20 karakter, hanya huruf kecil, angka, dan underscore.",
        )
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password minimal {MIN_PASSWORD_LENGTH} karakter.",
        )
    if job_title not in JOB_TITLES:
        raise HTTPException(status_code=400, detail="Job title tidak valid.")
    if email_registered(db, email):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar!")
    if username_taken(db, username):
        raise HTTPException(status_code=400, detail="Username sudah dipakai")

    hashed_password = auth.get_password_hash(payload.password)
    now = iso_utc(datetime.now(timezone.utc))

    # Tandai undangan terpakai dan buat akun dalam satu transaksi. UPDATE
    # bersyarat ini mengenai 0 baris kalau request lain sudah lebih dulu
    # memakai token yang sama, jadi token tidak bisa dipakai dua kali.
    claimed = (
        db.query(models.Invitation)
        .filter(
            models.Invitation.id == invitation.id,
            models.Invitation.used_at.is_(None),
        )
        .update({models.Invitation.used_at: now}, synchronize_session=False)
    )
    if claimed != 1:
        db.rollback()
        raise HTTPException(status_code=410, detail="Undangan sudah dipakai")

    try:
        db.add(
            models.User(
                name=name,
                username=username,
                email=email,
                role="Creator",
                job_title=job_title,
                password=hashed_password,
                account_status="Pending",
                created_at=now,
            )
        )
        db.commit()
    except IntegrityError:
        # Kalah balapan dengan pendaftaran lain yang memakai username/email
        # yang sama. Rollback juga membatalkan used_at undangan ini.
        db.rollback()
        if username_taken(db, username):
            raise HTTPException(status_code=400, detail="Username sudah dipakai")
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
        "username": u.username,
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
            models.User.username,
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

    # FK ke users tidak punya ON DELETE, jadi split, riwayat payout, dan
    # earning_history lama dihapus dulu (cascade di models.User mencakup split
    # dan earning_history).
    for model in (models.CreatorSplit, models.Payout, models.EarningHistory):
        db.query(model).filter(model.user_id == user_id).delete()
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
    if content_id is not None:
        query = query.filter(models.Content.id == content_id)
        split_query = split_query.filter(models.CreatorSplit.content_id == content_id)

    # Unit, gross, dan net all-time per konten (konten tanpa penjualan: 0).
    totals_by_content = {
        row["content_id"]: row for row in earnings.admin_overview(db)["by_content"]
    }

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
            "units_total": totals_by_content.get(c.id, {}).get("units", 0),
            "gross_usd": totals_by_content.get(c.id, {}).get("gross_usd", 0.0),
            "net_usd": totals_by_content.get(c.id, {}).get("net_usd", 0.0),
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
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    # Total, per konten, dan per bulan (opsional satu bulan YYYY-MM).
    return {"data": earnings.admin_overview(db, month=month)}


# ============================================================================
# SETTINGS (ADMIN)
# ============================================================================

def current_settings(db: Session) -> dict:
    return {
        "paypal_fee_pct": earnings.paypal_fee_pct(db),
        "idr_rate": earnings.idr_rate(db),
        "company_address": earnings.company_address(db),
    }


MAX_COMPANY_ADDRESS_LINES = 3  # sama dengan SLIP_ADDRESS_LINES
MAX_COMPANY_ADDRESS_LENGTH = 300


@app.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    return current_settings(db)


@app.put("/settings")
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    fee, rate = payload.paypal_fee_pct, payload.idr_rate

    if not (math.isfinite(fee) and 0 <= fee <= 100):
        raise HTTPException(status_code=400, detail="Fee PayPal harus antara 0 dan 100%.")
    if not (math.isfinite(rate) and rate > 0):
        raise HTTPException(status_code=400, detail="Kurs IDR harus lebih dari 0.")

    address = None
    if payload.company_address is not None:
        # Spasi di tepi tiap baris dan baris kosong dibuang.
        lines = [line.strip() for line in payload.company_address.splitlines() if line.strip()]
        address = "\n".join(lines)
        if not lines:
            raise HTTPException(status_code=400, detail="Alamat perusahaan wajib diisi.")
        if len(lines) > MAX_COMPANY_ADDRESS_LINES or len(address) > MAX_COMPANY_ADDRESS_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Alamat perusahaan maksimal {MAX_COMPANY_ADDRESS_LINES} baris "
                f"dan {MAX_COMPANY_ADDRESS_LENGTH} karakter.",
            )

    earnings.set_setting(db, "paypal_fee_pct", fee)
    earnings.set_setting(db, "idr_rate", rate)
    if address is not None:
        earnings.set_setting(db, "company_address", address)
    db.commit()
    return {"message": "Pengaturan disimpan.", "data": current_settings(db)}


# ============================================================================
# PENDAPATAN & PAYOUT KREATOR (ADMIN)
# ============================================================================

PAYOUT_METHODS = ("paypal", "bank", "ewallet")

# Periode payout: YYYY-MM.
MONTH_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


@app.get("/users/{user_id}/earnings")
def get_user_earnings(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    user = get_creator_or_error(db, user_id)
    # Data payout lengkap (tidak dimask): admin perlu untuk membayar.
    return {
        **earnings.creator_summary(db, user, include_internal=True),
        # Bulan lengkap yang bisa / sudah dibayar (form Catat pembayaran).
        "months": earnings.creator_months(db, user),
        "payout_method": user.payout_method,
        "payout_details": earnings.load_details(user.payout_details),
    }


MONTHS_ID = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
    "Agustus", "September", "Oktober", "November", "Desember",
)


def format_date_id(value: str) -> str:
    """YYYY-MM-DD -> "4 November 2026"."""
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return value
    return f"{d.day} {MONTHS_ID[d.month - 1]} {d.year}"


def format_month_id(value: str) -> str:
    """YYYY-MM -> "Oktober 2026"."""
    if not MONTH_RE.fullmatch(value or ""):
        return value
    return f"{MONTHS_ID[int(value[5:7]) - 1]} {value[:4]}"


def payout_shows_idr(payout: models.Payout) -> bool:
    """Rupiah hanya untuk payout non-PayPal yang punya snapshot kurs."""
    return payout.method != "paypal" and payout.amount_idr is not None and bool(payout.idr_rate)


# ----------------------------------------------------------------------------
# Slip payout PDF (payout_slip.py hanya tata letak; data disiapkan di sini)
# ----------------------------------------------------------------------------

SLIP_SENDER_NAME = "Squareclouds Studio"
SLIP_SENDER_EMAIL = "contact@squarecloudsmc.com"


# Karakter yang tidak boleh ada di nama file (Windows paling ketat).
UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def payout_period_label(payout: models.Payout) -> str:
    """"Agustus 2026" untuk nama file slip dan subjek email; payout lama tanpa
    periode memakai tanggal bayar ("3 November 2026")."""
    return format_month_id(payout.period_month) if payout.period_month else format_date_id(payout.paid_at)


def payout_slip_filename(user: models.User, payout: models.Payout) -> str:
    """"Payout Slip - <username> - <Bulan Tahun>.pdf", mis. "Payout Slip -
    cgartz - Agustus 2026.pdf". Akun lama tanpa username memakai nama."""
    who = user.username or user.name
    return UNSAFE_FILENAME_CHARS.sub("-", f"Payout Slip - {who} - {payout_period_label(payout)}.pdf")


SLIP_ADDRESS_LINES = 3


def slip_address_lines(address: str) -> list[str]:
    """Alamat perusahaan untuk blok pengirim slip: per baris, atau per koma
    kalau alamatnya satu baris. Maksimal 3 baris; sisanya digabung ke baris
    terakhir supaya tidak ada yang hilang."""
    lines = [line.strip() for line in address.splitlines() if line.strip()]
    if len(lines) == 1:
        lines = [part.strip() for part in lines[0].split(",") if part.strip()]
    if len(lines) > SLIP_ADDRESS_LINES:
        lines = lines[: SLIP_ADDRESS_LINES - 1] + [", ".join(lines[SLIP_ADDRESS_LINES - 1:])]
    return lines


def payout_slip_pdf(db: Session, user: models.User, payout: models.Payout) -> bytes:
    """Slip PDF di memori (tidak pernah ditulis ke disk/DB); dibuat ulang tiap
    kali dikirim: payout baru, kirim ulang email, upload ulang ke Drive.
    Hanya bagian kreator per konten; unit, gross/net/fee/split, dan bagian
    Squareclouds tidak pernah masuk slip."""
    show_idr = payout_shows_idr(payout)
    return payout_slip.render(payout_slip.SlipData(
        title=payout_slip_filename(user, payout).removesuffix(".pdf"),
        created_on=format_date_id(payout.paid_at),
        revenue_month=format_month_id(payout.period_month) if payout.period_month else "-",
        sender=[SLIP_SENDER_NAME, SLIP_SENDER_EMAIL, *slip_address_lines(earnings.company_address(db))],
        # Baris username dilewati untuk akun lama tanpa username.
        recipient=[
            line
            for line in (
                user.name,
                f"{user.username} - Squareclouds Studio" if user.username else None,
                user.email,
            )
            if line
        ],
        items=[(i.content_name, earnings.format_usd(i.share_usd)) for i in payout.items],
        total_usd=earnings.format_usd(payout.amount_usd),
        exchange_rate=f"{earnings.format_idr(payout.idr_rate)}/$" if show_idr else None,
        total_idr=earnings.format_idr(payout.amount_idr) if show_idr else None,
        note=payout.note,
    ))


def send_payout_email(
    db: Session, user: models.User, payout: models.Payout, pdf: bytes | None = None
) -> bool:
    """Email singkat: periode, tanggal bayar, dan slip PDF terlampir.

    Jumlah, rupiah, kurs, tujuan, catatan, dan rincian konten sengaja tidak
    ditulis di email; semuanya hanya ada di slip.
    """
    link = f"{portal_url()}/creator"
    rows = [("Tanggal", format_date_id(payout.paid_at))]
    # Payout lama (sebelum payout per bulan) tidak punya periode.
    if payout.period_month:
        rows.insert(0, ("Periode", format_month_id(payout.period_month)))

    text = (
        f"Halo {user.name},\n\n"
        "Payout pendapatan Anda dari Squareclouds Studio telah dikirim.\n\n"
        + "\n".join(f"{label:8}: {value}" for label, value in rows)
        + "\n\nSlip payout (PDF) terlampir.\n\n"
        f"Buka dashboard: {link}\n\n"
        "Salam,\nSquareclouds Studio"
    )
    html_rows = "".join(
        f'<tr><td style="padding:4px 16px 4px 0;color:#6b7280">{label}</td>'
        f'<td style="padding:4px 0;font-weight:bold">{escape(value)}</td></tr>'
        for label, value in rows
    )
    html = f"""\
<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937;line-height:1.6">
  <p>Halo {escape(user.name)},</p>
  <p>Payout pendapatan Anda dari <b>Squareclouds Studio</b> telah dikirim.</p>
  <table style="border-collapse:collapse;margin:8px 0 16px">{html_rows}</table>
  <p>Slip payout (PDF) terlampir.</p>
  <p><a href="{escape(link)}" style="display:inline-block;padding:10px 20px;border-radius:8px;
     background:#2563eb;color:#ffffff;text-decoration:none;font-weight:bold">Buka dashboard</a></p>
  <p>Salam,<br>Squareclouds Studio</p>
</div>"""
    pdf = pdf or payout_slip_pdf(db, user, payout)
    attachment = (payout_slip_filename(user, payout), pdf, "application/pdf")
    return mailer.send_mail(
        user.email,
        f"Payout Squareclouds Studio - {payout_period_label(payout)}",
        html,
        text,
        attachments=[attachment],
    )


def notify_payout(db: Session, payout: models.Payout, pdf: bytes | None = None) -> bool:
    """Kirim email payout ke kreator; notified_at diisi kalau terkirim.

    pdf: slip yang sudah dibuat (POST /payouts memakai slip yang sama untuk
    email dan Drive); None = dibuat di sini (kirim ulang email).

    Gagal kirim (error SMTP, atau SMTP belum dikonfigurasi) hanya dicatat ke
    log: payout yang sudah tersimpan tidak pernah dibatalkan karena email.
    """
    user = db.get(models.User, payout.user_id)
    try:
        sent = send_payout_email(db, user, payout, pdf)
    except Exception as e:
        print(f"Payout Mail Error (payout {payout.id}): {e}", flush=True)
        return False
    if not sent:
        return False
    try:
        payout.notified_at = iso_utc(datetime.now(timezone.utc))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Payout notified_at Error (payout {payout.id}): {e}", flush=True)
        return False
    return True


def drive_subfolder(payout: models.Payout) -> str:
    """Subfolder Drive per tahun-bulan periode; payout lama: bulan bayar."""
    return payout.period_month or payout.paid_at[:7]


def upload_payout_slip(db: Session, payout: models.Payout, pdf: bytes | None = None) -> bool:
    """Arsipkan slip PDF ke Google Drive; drive_file_id diisi kalau berhasil.

    Drive belum dikonfigurasi (GDRIVE_* kosong) atau upload gagal hanya
    dicatat ke log: payout tidak pernah dibatalkan karena Drive. Admin bisa
    upload ulang (POST /payouts/{id}/drive).
    """
    user = db.get(models.User, payout.user_id)
    try:
        pdf = pdf or payout_slip_pdf(db, user, payout)
        file_id = gdrive.upload_pdf(payout_slip_filename(user, payout), pdf, drive_subfolder(payout))
    except gdrive.DriveNotConfigured as e:
        print(f"Payout Drive dilewati (payout {payout.id}): {e}", flush=True)
        return False
    except Exception as e:
        print(f"Payout Drive Error (payout {payout.id}): {e}", flush=True)
        return False
    try:
        payout.drive_file_id = file_id
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Payout drive_file_id Error (payout {payout.id}, file {file_id}): {e}", flush=True)
        return False
    return True


@app.post("/payouts", status_code=status.HTTP_201_CREATED)
def create_payout(
    payload: schemas.PayoutCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    # Kunci baris kreator (PostgreSQL) supaya dua pencatatan bersamaan tidak
    # bisa sama-sama lolos cek "sudah dibayar" dan saldo tertunda. Unique
    # index (user_id, period_month) tetap jadi pengaman terakhir.
    user = (
        db.query(models.User)
        .filter(models.User.id == payload.user_id)
        .with_for_update()
        .first()
    )
    if not user or user.role != "Creator":
        raise HTTPException(status_code=404, detail="Kreator tidak ditemukan")
    if user.account_status != "Active":
        raise HTTPException(status_code=400, detail="Payout hanya untuk kreator berstatus Active.")
    if user.payout_method not in PAYOUT_METHODS:
        raise HTTPException(status_code=400, detail="Kreator belum mengisi metode payout.")

    # Jumlah selalu dihitung server: bagian kreator di bulan itu.
    period = payload.period_month.strip()
    if not MONTH_RE.fullmatch(period):
        raise HTTPException(status_code=400, detail="Periode harus berformat YYYY-MM.")
    label = format_month_id(period)
    month = next((m for m in earnings.creator_months(db, user) if m["month"] == period), None)
    if month is None:
        last_complete = earnings.last_complete_month(db)
        if last_complete is None or period > last_complete:
            raise HTTPException(
                status_code=400,
                detail=f"Periode {label} belum lengkap; hanya bulan yang sudah lewat yang bisa dibayar.",
            )
        raise HTTPException(status_code=400, detail=f"Tidak ada pendapatan untuk periode {label}.")
    if month["paid"]:
        raise HTTPException(status_code=400, detail=f"Periode {label} sudah dibayar.")
    amount = month["share_usd"]
    if amount <= 0:
        raise HTTPException(status_code=400, detail=f"Tidak ada pendapatan untuk periode {label}.")
    # Bisa terjadi kalau masih ada payout lama tanpa periode yang sudah
    # menutup sebagian pendapatan bulan ini.
    outstanding = earnings.creator_summary(db, user, include_internal=False)["outstanding_usd"]
    if amount > outstanding:
        raise HTTPException(
            status_code=400,
            detail=f"Jumlah payout melebihi saldo tertunda (${outstanding:,.2f}).",
        )

    paid_at = (payload.paid_at or "").strip()
    if paid_at:
        try:
            paid_at = date.fromisoformat(paid_at).isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Tanggal bayar harus berformat YYYY-MM-DD.")
    else:
        paid_at = datetime.now(timezone.utc).date().isoformat()

    payout = models.Payout(
        user_id=user.id,
        period_month=period,
        amount_usd=amount,
        idr_rate=earnings.idr_rate(db),
        # None untuk PayPal (creator_months hanya mengisinya untuk bank/e-wallet).
        amount_idr=month["share_idr"],
        method=user.payout_method,
        details=user.payout_details or "{}",
        note=(payload.note or "").strip() or None,
        paid_at=paid_at,
        created_by=current_user.id,
        created_at=iso_utc(datetime.now(timezone.utc)),
    )
    # Rincian per konten disalin dari bulan itu; Σ share_usd = amount_usd.
    splits = dict(
        db.query(models.CreatorSplit.content_id, models.CreatorSplit.split_percentage)
        .filter(models.CreatorSplit.user_id == user.id)
    )
    payout.items = [
        models.PayoutItem(
            content_id=item["content_id"],
            content_name=item["name"],
            units=item["units"],
            share_usd=item["share_usd"],
            split_pct=splits[item["content_id"]],
        )
        for item in month["items"]
    ]
    db.add(payout)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Periode {label} sudah dibayar.")
    db.refresh(payout)

    # Setelah commit, supaya email atau Drive yang gagal tidak membatalkan
    # payout. Slip dibuat sekali di memori: dikirim lewat email, lalu file
    # yang sama diarsipkan ke Google Drive.
    try:
        pdf = payout_slip_pdf(db, user, payout)
    except Exception as e:
        print(f"Payout Slip Error (payout {payout.id}): {e}", flush=True)
        pdf = None
    notified = notify_payout(db, payout, pdf)
    drive_saved = upload_payout_slip(db, payout, pdf)
    db.refresh(payout)
    message = f"Payout {label} (${amount:,.2f}) untuk {user.name} dicatat."
    return {
        "message": message
        + (
            " Email notifikasi terkirim."
            if notified
            else " Email notifikasi gagal dikirim; kirim ulang dari riwayat payout."
        )
        + (
            " Slip tersimpan di Google Drive."
            if drive_saved
            else " Slip gagal disimpan ke Google Drive; upload ulang dari riwayat payout."
        ),
        "notified": notified,
        "drive_saved": drive_saved,
        "data": earnings.serialize_payout(payout, include_internal=True),
    }


@app.post("/payouts/{payout_id}/notify")
def resend_payout_email(
    payout_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    payout = db.query(models.Payout).filter(models.Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout tidak ditemukan")
    if payout.notified_at:
        raise HTTPException(status_code=400, detail="Email untuk payout ini sudah terkirim.")
    if not notify_payout(db, payout):
        raise HTTPException(
            status_code=502,
            detail="Email gagal dikirim. Cek konfigurasi SMTP lalu coba lagi.",
        )
    db.refresh(payout)
    return {
        "message": "Email payout terkirim.",
        "data": earnings.serialize_payout(payout, include_internal=True),
    }


@app.delete("/payouts/{payout_id}")
def delete_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    payout = db.query(models.Payout).filter(models.Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout tidak ditemukan")
    drive_file_id = payout.drive_file_id
    db.delete(payout)
    db.commit()
    # Slip di Drive ikut dihapus; error diabaikan (cukup dicatat ke log).
    if drive_file_id:
        try:
            gdrive.delete_file(drive_file_id)
        except Exception as e:
            print(f"Payout Drive Delete Error (file {drive_file_id}): {e}", flush=True)
    return {"message": "Payout dihapus."}


@app.post("/payouts/{payout_id}/drive")
def reupload_payout_slip(
    payout_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    payout = db.query(models.Payout).filter(models.Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout tidak ditemukan")
    if payout.drive_file_id:
        raise HTTPException(status_code=400, detail="Slip payout ini sudah tersimpan di Google Drive.")
    if not upload_payout_slip(db, payout):
        raise HTTPException(
            status_code=502,
            detail="Upload ke Google Drive gagal. Cek GDRIVE_SA_FILE, GDRIVE_FOLDER_ID, dan akses "
            "service account ke folder, lalu coba lagi.",
        )
    db.refresh(payout)
    return {
        "message": "Slip payout tersimpan di Google Drive.",
        "data": earnings.serialize_payout(payout, include_internal=True),
    }


# ============================================================================
# METODE PAYOUT (KREATOR)
# ============================================================================

# Sama dengan EWALLET_PROVIDERS di frontend/src/lib/portal.ts.
EWALLET_PROVIDERS = ("DANA", "GoPay", "OVO", "ShopeePay")
ACCOUNT_NUMBER_RE = re.compile(r"\d{6,20}")
# Nomor HP Indonesia 10–13 digit, setelah awalan +62/62 diganti 0.
PHONE_RE = re.compile(r"08\d{8,11}")
MAX_PAYOUT_TEXT_LENGTH = 100
# Field yang dimask di respons kreator: email jadi "re***@gmail.com", nomor
# rekening/HP hanya 4 digit terakhir yang terlihat.
MASKED_PAYOUT_FIELDS = ("paypal_email", "account_number", "phone")


def require_creator(user):
    if user.role != "Creator":
        raise HTTPException(status_code=403, detail="Akses ditolak.")


def mask_value(value: str) -> str:
    return "*" * max(len(value) - 4, 0) + value[-4:]


def mask_email(value: str) -> str:
    local, at, domain = value.partition("@")
    return f"{local[:2]}***@{domain}" if at else mask_value(value)


def mask_payout_details(details: dict | None) -> dict | None:
    if details is None:
        return None
    masked = {}
    for key, value in details.items():
        if key in MASKED_PAYOUT_FIELDS and value:
            value = mask_email(str(value)) if key == "paypal_email" else mask_value(str(value))
        masked[key] = value
    return masked


def clean_payout_details(method: str, raw: dict) -> dict:
    """Validasi data payout per metode; hanya field yang dikenal yang disimpan."""

    def text(key: str, label: str) -> str:
        value = str(raw.get(key) or "").strip()
        if not value:
            raise HTTPException(status_code=400, detail=f"{label} wajib diisi.")
        if len(value) > MAX_PAYOUT_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"{label} maksimal {MAX_PAYOUT_TEXT_LENGTH} karakter.",
            )
        return value

    def digits(key: str) -> str:
        # Spasi, titik, dan strip pemisah angka diabaikan.
        return re.sub(r"[\s.-]", "", str(raw.get(key) or ""))

    if method == "paypal":
        email = text("paypal_email", "Email PayPal").lower()
        if not EMAIL_RE.fullmatch(email):
            raise HTTPException(status_code=400, detail="Format email PayPal tidak valid.")
        return {"paypal_email": email}

    if method == "bank":
        bank_name = text("bank_name", "Nama bank")
        account_number = digits("account_number")
        if not ACCOUNT_NUMBER_RE.fullmatch(account_number):
            raise HTTPException(status_code=400, detail="Nomor rekening harus 6–20 digit angka.")
        return {
            "bank_name": bank_name,
            "account_number": account_number,
            "account_name": text("account_name", "Nama pemilik rekening"),
        }

    if method == "ewallet":
        provider = str(raw.get("provider") or "").strip()
        if provider not in EWALLET_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Provider e-wallet harus salah satu dari: {', '.join(EWALLET_PROVIDERS)}.",
            )
        phone = re.sub(r"^\+?62", "0", digits("phone"))
        if not PHONE_RE.fullmatch(phone):
            raise HTTPException(
                status_code=400,
                detail="Nomor HP harus nomor Indonesia 10–13 digit (contoh 081234567890).",
            )
        return {
            "provider": provider,
            "phone": phone,
            "account_name": text("account_name", "Nama pemilik akun"),
        }

    raise HTTPException(status_code=400, detail="Metode payout harus paypal, bank, atau ewallet.")


def serialize_payout_preference(user: models.User) -> dict:
    return {
        "payout_method": user.payout_method,
        "payout_details_masked": mask_payout_details(earnings.load_details(user.payout_details)),
    }


@app.get("/me/payout")
def get_my_payout(current_user: models.User = Depends(get_current_user)):
    require_creator(current_user)
    return serialize_payout_preference(current_user)


@app.put("/me/payout")
def update_my_payout(
    payload: schemas.PayoutPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_creator(current_user)
    method = payload.payout_method.strip().lower()
    details = clean_payout_details(method, payload.payout_details)

    current_user.payout_method = method
    current_user.payout_details = json.dumps(details, ensure_ascii=False)
    db.commit()
    db.refresh(current_user)
    return {"message": "Metode payout disimpan.", **serialize_payout_preference(current_user)}


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

    # Hanya unit dan bagian kreator: harga, gross, net, split %, dan bagian
    # Squareclouds tidak pernah dikirim ke kreator (lihat earnings.py).
    projects = (
        db.query(models.Content)
        .join(models.CreatorSplit, models.CreatorSplit.content_id == models.Content.id)
        .filter(models.CreatorSplit.user_id == current_user.id)
        .order_by(models.Content.name)
        .all()
    )
    daily = (
        db.query(models.DailySales.date, models.Content.name, models.DailySales.quantity)
        .join(models.Content, models.Content.id == models.DailySales.content_id)
        .join(models.CreatorSplit, models.CreatorSplit.content_id == models.Content.id)
        .filter(models.CreatorSplit.user_id == current_user.id)
        .order_by(models.DailySales.date)
        .all()
    )

    return {
        "nama": current_user.name,
        "job_title": current_user.job_title,
        "proyek": [
            {
                "name": c.name,
                "status": c.status,
                "pack_type": c.pack_type,
                "release_date": c.release_date,
            }
            for c in projects
        ],
        "grafik_harian": [
            {"date": d, "content_name": name, "quantity": quantity}
            for d, name, quantity in daily
        ],
        **earnings.creator_summary(db, current_user, include_internal=False),
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
