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
import mailer
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
    }


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

    earnings.set_setting(db, "paypal_fee_pct", fee)
    earnings.set_setting(db, "idr_rate", rate)
    db.commit()
    return {"message": "Pengaturan disimpan.", "data": current_settings(db)}


# ============================================================================
# PENDAPATAN & PAYOUT KREATOR (ADMIN)
# ============================================================================

PAYOUT_METHODS = ("paypal", "bank", "ewallet")


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


def payout_destination_text(method: str, details: dict | None) -> str:
    """Tujuan payout termask, mis. "Transfer bank BCA ****1234"."""
    details = details or {}
    if method == "paypal":
        return f"PayPal {mask_email(str(details.get('paypal_email') or ''))}".strip()
    if method == "bank":
        number = str(details.get("account_number") or "")
        return f"Transfer bank {details.get('bank_name') or ''} ****{number[-4:]}"
    if method == "ewallet":
        phone = str(details.get("phone") or "")
        return f"{details.get('provider') or 'E-wallet'} ****{phone[-4:]}"
    return method


def send_payout_email(user: models.User, payout: models.Payout) -> bool:
    amount = f"${payout.amount_usd:,.2f}"
    # Rupiah dari snapshot payout (dihitung earnings.to_idr saat dicatat).
    idr = (
        f"≈ {earnings.format_idr(payout.amount_idr)} (kurs {earnings.format_idr(payout.idr_rate)}/$)"
        if payout.method != "paypal" and payout.amount_idr is not None and payout.idr_rate
        else None
    )
    destination = payout_destination_text(payout.method, earnings.load_details(payout.details))
    paid_on = format_date_id(payout.paid_at)
    link = f"{portal_url()}/creator"

    rows = [("Jumlah", amount + (f"\n{idr}" if idr else "")), ("Tujuan", destination), ("Tanggal", paid_on)]
    if payout.note:
        rows.append(("Catatan", payout.note))

    text = (
        f"Halo {user.name},\n\n"
        "Payout pendapatan Anda dari Squareclouds Studio telah dikirim.\n\n"
        + "\n".join(f"{label:8}: {value}".replace("\n", "\n" + " " * 10) for label, value in rows)
        + "\n\nLihat rincian pendapatan dan riwayat payout di dashboard:\n"
        f"{link}\n\n"
        "Salam,\nSquareclouds Studio"
    )
    html_rows = "".join(
        f'<tr><td style="padding:4px 16px 4px 0;color:#6b7280;vertical-align:top">{label}</td>'
        f'<td style="padding:4px 0;font-weight:bold">{escape(value).replace(chr(10), "<br>")}</td></tr>'
        for label, value in rows
    )
    html = f"""\
<div style="font-family:Arial,sans-serif;font-size:14px;color:#1f2937;line-height:1.6">
  <p>Halo {escape(user.name)},</p>
  <p>Payout pendapatan Anda dari <b>Squareclouds Studio</b> telah dikirim.</p>
  <table style="border-collapse:collapse;margin:8px 0 16px">{html_rows}</table>
  <p><a href="{escape(link)}" style="display:inline-block;padding:10px 20px;border-radius:8px;
     background:#2563eb;color:#ffffff;text-decoration:none;font-weight:bold">Buka dashboard</a></p>
  <p style="font-size:12px;color:#6b7280">Atau buka link ini: {escape(link)}</p>
  <p>Salam,<br>Squareclouds Studio</p>
</div>"""
    return mailer.send_mail(
        user.email, f"Payout Squareclouds Studio: {amount} telah dikirim", html, text
    )


def notify_payout(db: Session, payout: models.Payout) -> bool:
    """Kirim email payout ke kreator; notified_at diisi kalau terkirim.

    Gagal kirim (error SMTP, atau SMTP belum dikonfigurasi) hanya dicatat ke
    log: payout yang sudah tersimpan tidak pernah dibatalkan karena email.
    """
    user = db.get(models.User, payout.user_id)
    try:
        sent = send_payout_email(user, payout)
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


@app.post("/payouts", status_code=status.HTTP_201_CREATED)
def create_payout(
    payload: schemas.PayoutCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_admin(current_user)
    # Kunci baris kreator (PostgreSQL) supaya dua pencatatan bersamaan tidak
    # bisa sama-sama lolos cek saldo tertunda.
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

    if not math.isfinite(payload.amount_usd):
        raise HTTPException(status_code=400, detail="Jumlah payout tidak valid.")
    amount = round(payload.amount_usd, 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Jumlah payout harus lebih dari 0.")
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

    rate = earnings.idr_rate(db)
    payout = models.Payout(
        user_id=user.id,
        amount_usd=amount,
        idr_rate=rate,
        amount_idr=earnings.to_idr(amount, rate) if user.payout_method in earnings.IDR_METHODS else None,
        method=user.payout_method,
        details=user.payout_details or "{}",
        note=(payload.note or "").strip() or None,
        paid_at=paid_at,
        created_by=current_user.id,
        created_at=iso_utc(datetime.now(timezone.utc)),
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)

    # Setelah commit, supaya email yang gagal tidak membatalkan payout.
    notified = notify_payout(db, payout)
    db.refresh(payout)
    message = f"Payout ${amount:,.2f} untuk {user.name} dicatat."
    return {
        "message": message
        + (
            " Email notifikasi terkirim."
            if notified
            else " Email notifikasi gagal dikirim; kirim ulang dari riwayat payout."
        ),
        "notified": notified,
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
    db.delete(payout)
    db.commit()
    return {"message": "Payout dihapus."}


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
