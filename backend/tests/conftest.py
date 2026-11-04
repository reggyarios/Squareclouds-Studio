"""Fixture uji backend: database SQLite sementara + TestClient.

Jalankan dari folder backend:
    venv/bin/pip install -r requirements-dev.txt
    venv/bin/python -m pytest tests
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Diset sebelum `database` di-import. load_dotenv tidak menimpa variabel yang
# sudah ada, jadi DATABASE_URL dan SMTP dari .env tidak ikut terpakai.
TMP_DIR = tempfile.mkdtemp(prefix="squareclouds-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(TMP_DIR) / 'test.db'}"
os.environ["SMTP_HOST"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import mailer  # noqa: E402
import main  # noqa: E402
import models  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password"


@pytest.fixture(scope="session", autouse=True)
def cleanup_tmp_dir():
    yield
    engine.dispose()
    shutil.rmtree(TMP_DIR, ignore_errors=True)


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def admin_headers(client):
    with SessionLocal() as db:
        db.add(
            models.User(
                name="Admin",
                email=ADMIN_EMAIL,
                role="Admin",
                password=auth.get_password_hash(ADMIN_PASSWORD),
                account_status="Active",
            )
        )
        db.commit()
    res = client.post("/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def outbox(monkeypatch):
    """Ganti mailer.send_mail: email ditampung di list, dianggap terkirim."""
    sent = []

    def fake_send_mail(to, subject, html, text):
        sent.append({"to": to, "subject": subject, "html": html, "text": text})
        return True

    monkeypatch.setattr(mailer, "send_mail", fake_send_mail)
    return sent
