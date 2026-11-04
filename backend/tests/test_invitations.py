"""Alur undangan kreator: kirim undangan -> cek token -> daftar."""
import re
from datetime import datetime, timedelta, timezone

import models
from database import SessionLocal

CREATOR_PASSWORD = "creator-password"


def invite(client, headers, email):
    res = client.post("/invitations", json={"email": email}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def token_from(mail):
    match = re.search(r"/register\?token=([\w-]+)", mail["text"])
    assert match, mail["text"]
    return match.group(1)


def register(client, token, **overrides):
    body = {
        "token": token,
        "name": "Kreator Baru",
        "password": CREATOR_PASSWORD,
        "job_title": "Builder",
        **overrides,
    }
    return client.post("/register", json=body)


def find(model, *criteria):
    with SessionLocal() as db:
        return db.query(model).filter(*criteria).all()


def test_invitations_require_admin_token(client):
    assert client.post("/invitations", json={"email": "a@example.com"}).status_code == 401
    assert client.get("/invitations").status_code == 401


def test_valid_token_registers_pending_creator(client, admin_headers, outbox):
    data = invite(client, admin_headers, "  New.Creator@Example.com ")
    assert data["sent"] is True

    assert len(outbox) == 1
    mail = outbox[0]
    assert mail["to"] == "new.creator@example.com"
    assert mail["subject"] == "Undangan Creator Portal Squareclouds Studio"
    token = token_from(mail)
    assert f"https://creator.squarecloudsmc.com/register?token={token}" in mail["text"]

    listed = client.get("/invitations", headers=admin_headers).json()["data"]
    assert [i["email"] for i in listed] == ["new.creator@example.com"]
    assert listed[0]["expired"] is False
    assert "token" not in listed[0]

    res = client.get(f"/register/{token}")
    assert res.status_code == 200
    assert res.json() == {"email": "new.creator@example.com"}

    # Email di body diabaikan; yang dipakai email dari undangan.
    res = register(client, token, email="lain@example.com")
    assert res.status_code == 201, res.text
    assert res.json() == {"message": "Pendaftaran diterima. Tunggu persetujuan admin."}

    [user] = find(models.User, models.User.role == "Creator")
    assert user.email == "new.creator@example.com"
    assert user.account_status == "Pending"
    assert user.password != CREATOR_PASSWORD
    assert not find(models.User, models.User.email == "lain@example.com")

    [invitation] = find(models.Invitation)
    assert invitation.used_at is not None
    assert client.get("/invitations", headers=admin_headers).json()["data"] == []


def test_login_pending_then_approved_ignores_email_case(client, admin_headers, outbox):
    invite(client, admin_headers, "creator@example.com")
    assert register(client, token_from(outbox[0])).status_code == 201

    login = {"username": "Creator@Example.COM", "password": CREATOR_PASSWORD}
    res = client.post("/login", data=login)
    assert res.status_code == 403
    assert res.json()["detail"] == "Akun belum disetujui admin."

    [user] = find(models.User, models.User.role == "Creator")
    res = client.put(f"/users/{user.id}", json={"account_status": "Active"}, headers=admin_headers)
    assert res.status_code == 200, res.text

    res = client.post("/login", data=login)
    assert res.status_code == 200, res.text
    assert res.json()["role"] == "Creator"


def test_wrong_or_missing_token_is_404(client):
    res = client.get("/register/token-salah")
    assert res.status_code == 404
    assert res.json()["detail"] == "Undangan tidak ditemukan"

    res = register(client, "token-salah")
    assert res.status_code == 404
    assert res.json()["detail"] == "Undangan tidak ditemukan"

    res = register(client, None)
    assert res.status_code == 404
    assert res.json()["detail"] == "Undangan tidak ditemukan"

    assert not find(models.User)


def test_expired_token_is_410(client, admin_headers, outbox):
    invite(client, admin_headers, "creator@example.com")
    token = token_from(outbox[0])

    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    with SessionLocal() as db:
        db.query(models.Invitation).update({"expires_at": past.isoformat(timespec="seconds")})
        db.commit()

    res = client.get(f"/register/{token}")
    assert res.status_code == 410
    assert res.json()["detail"] == "Undangan sudah kedaluwarsa"

    res = register(client, token)
    assert res.status_code == 410
    assert res.json()["detail"] == "Undangan sudah kedaluwarsa"
    assert not find(models.User, models.User.role == "Creator")

    [listed] = client.get("/invitations", headers=admin_headers).json()["data"]
    assert listed["expired"] is True


def test_used_token_is_410(client, admin_headers, outbox):
    invite(client, admin_headers, "creator@example.com")
    token = token_from(outbox[0])
    assert register(client, token).status_code == 201

    res = client.get(f"/register/{token}")
    assert res.status_code == 410
    assert res.json()["detail"] == "Undangan sudah dipakai"

    res = register(client, token, name="Orang Lain")
    assert res.status_code == 410
    assert res.json()["detail"] == "Undangan sudah dipakai"
    assert len(find(models.User, models.User.role == "Creator")) == 1


def test_reinvite_replaces_previous_token(client, admin_headers, outbox):
    invite(client, admin_headers, "creator@example.com")
    invite(client, admin_headers, "Creator@example.com")
    old_token, new_token = token_from(outbox[0]), token_from(outbox[1])
    assert old_token != new_token

    assert client.get(f"/register/{old_token}").status_code == 404
    assert client.get(f"/register/{new_token}").status_code == 200
    assert len(client.get("/invitations", headers=admin_headers).json()["data"]) == 1


def test_cancelled_invitation_token_is_404(client, admin_headers, outbox):
    invite(client, admin_headers, "creator@example.com")
    [listed] = client.get("/invitations", headers=admin_headers).json()["data"]

    res = client.delete(f"/invitations/{listed['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert client.get(f"/register/{token_from(outbox[0])}").status_code == 404


def test_invite_rejects_registered_email(client, admin_headers, outbox):
    res = client.post("/invitations", json={"email": "ADMIN@example.com"}, headers=admin_headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "Email sudah terdaftar!"

    res = client.post("/invitations", json={"email": "bukan-email"}, headers=admin_headers)
    assert res.status_code == 400
    assert outbox == []


def test_invite_without_smtp_logs_email(client, admin_headers, capsys):
    data = invite(client, admin_headers, "creator@example.com")
    assert data["sent"] is False
    assert "/register?token=" in capsys.readouterr().out
