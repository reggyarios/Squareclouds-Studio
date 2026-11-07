"""Arsip slip payout di Google Drive (service account).

Konfigurasi dari backend/.env (lihat .env.example):
    GDRIVE_SA_FILE    path file JSON kunci service account
    GDRIVE_FOLDER_ID  ID folder induk arsip slip

Service account tidak punya kuota penyimpanan sendiri, jadi folder induk harus
ada di Shared Drive dengan service account sebagai anggota (Content manager,
supaya bisa menghapus juga). Semua panggilan memakai supportsAllDrives=True.

Slip disimpan di subfolder per periode ("2026-08") di bawah folder induk;
subfolder dibuat otomatis kalau belum ada.

Salah satu env kosong = tidak dikonfigurasi: upload_pdf/delete_file melempar
DriveNotConfigured. Pemanggil (main.upload_payout_slip) hanya mencatatnya ke
log; payout tidak pernah gagal karena Drive.
"""
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

load_dotenv(Path(__file__).resolve().parent / ".env")

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveNotConfigured(Exception):
    """GDRIVE_SA_FILE atau GDRIVE_FOLDER_ID kosong."""


def _config() -> tuple[str, str]:
    sa_file = os.getenv("GDRIVE_SA_FILE", "").strip()
    folder_id = os.getenv("GDRIVE_FOLDER_ID", "").strip()
    if not (sa_file and folder_id):
        raise DriveNotConfigured("GDRIVE_SA_FILE / GDRIVE_FOLDER_ID belum diisi")
    return sa_file, folder_id


def _service(sa_file: str):
    creds = service_account.Credentials.from_service_account_file(sa_file, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _quote(value: str) -> str:
    """Nilai string untuk query files.list (kutip tunggal di-escape)."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _subfolder(service, parent_id: str, name: str) -> str:
    """ID subfolder `name` langsung di bawah parent_id; dibuat kalau belum ada."""
    found = service.files().list(
        q=(
            f"name = {_quote(name)} and mimeType = '{FOLDER_MIME}' "
            f"and {_quote(parent_id)} in parents and trashed = false"
        ),
        fields="files(id)",
        pageSize=1,
        corpora="allDrives",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute()
    if found.get("files"):
        return found["files"][0]["id"]
    folder = service.files().create(
        body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return folder["id"]


def upload_pdf(filename: str, data: bytes, subfolder: str) -> str:
    """Upload PDF ke <folder induk>/<subfolder>/<filename>; mengembalikan file ID.

    Error API/jaringan diteruskan ke pemanggil.
    """
    sa_file, folder_id = _config()
    service = _service(sa_file)
    parent = _subfolder(service, folder_id, subfolder)
    created = service.files().create(
        body={"name": filename, "parents": [parent]},
        media_body=MediaIoBaseUpload(io.BytesIO(data), mimetype="application/pdf", resumable=False),
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return created["id"]


def delete_file(file_id: str) -> None:
    """Hapus file dari Drive. Error diteruskan ke pemanggil."""
    sa_file, _ = _config()
    _service(sa_file).files().delete(fileId=file_id, supportsAllDrives=True).execute()
