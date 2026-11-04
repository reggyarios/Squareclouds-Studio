"""Manajemen kreator oleh admin."""
import auth
import models
from database import SessionLocal

CREATOR_EMAIL = "creator@example.com"
CREATOR_PASSWORD = "creator-password"


def add_creator(db, email, name="Kreator"):
    creator = models.User(
        name=name,
        email=email,
        role="Creator",
        job_title="Builder",
        password=auth.get_password_hash(CREATOR_PASSWORD),
        account_status="Active",
    )
    db.add(creator)
    db.flush()
    return creator


def test_delete_creator_removes_splits_and_history(client, admin_headers):
    with SessionLocal() as db:
        creator = add_creator(db, CREATOR_EMAIL)
        other = add_creator(db, "lain@example.com", name="Kreator Lain")
        contents = [models.Content(name=f"Konten {i}") for i in range(2)]
        db.add_all(contents)
        db.flush()
        db.add_all(
            [models.CreatorSplit(user_id=creator.id, content_id=c.id, split_percentage=30) for c in contents]
            + [models.CreatorSplit(user_id=other.id, content_id=contents[0].id, split_percentage=20)]
            + [
                models.EarningHistory(user_id=u.id, content_name="Konten 0", amount=5, report_month="2026-10")
                for u in (creator, other)
            ]
        )
        db.commit()
        creator_id, other_id = creator.id, other.id

    res = client.delete(f"/users/{creator_id}", headers=admin_headers)
    assert res.status_code == 200, res.text

    with SessionLocal() as db:
        assert db.get(models.User, creator_id) is None
        for model in (models.CreatorSplit, models.EarningHistory):
            assert db.query(model).filter(model.user_id == creator_id).count() == 0
            assert db.query(model).filter(model.user_id == other_id).count() == 1
        assert db.query(models.Content).count() == 2

    [content] = [c for c in client.get("/contents/", headers=admin_headers).json()["data"] if c["splits"]]
    assert [s["user_id"] for s in content["splits"]] == [other_id]
    assert client.delete(f"/users/{creator_id}", headers=admin_headers).status_code == 404


def test_delete_user_rejects_admin_and_requires_admin(client, admin_headers):
    with SessionLocal() as db:
        admin_id = db.query(models.User.id).filter(models.User.role == "Admin").scalar()
        creator_id = add_creator(db, CREATOR_EMAIL).id
        db.commit()

    res = client.delete(f"/users/{admin_id}", headers=admin_headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "Akun Admin tidak bisa diubah dari sini."

    assert client.delete(f"/users/{creator_id}").status_code == 401
    login = {"username": CREATOR_EMAIL, "password": CREATOR_PASSWORD}
    creator_token = client.post("/login", data=login).json()["access_token"]
    res = client.delete(f"/users/{creator_id}", headers={"Authorization": f"Bearer {creator_token}"})
    assert res.status_code == 403

    with SessionLocal() as db:
        assert db.query(models.User).count() == 2


def test_admin_cannot_change_creator_password(client, admin_headers):
    with SessionLocal() as db:
        creator = models.User(
            name="Kreator",
            email=CREATOR_EMAIL,
            role="Creator",
            job_title="Builder",
            password=auth.get_password_hash(CREATOR_PASSWORD),
            account_status="Active",
        )
        db.add(creator)
        db.commit()
        creator_id = creator.id

    res = client.put(
        f"/users/{creator_id}",
        json={"password": "password-dari-admin", "job_title": "Developer"},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["job_title"] == "Developer"

    login = {"username": CREATOR_EMAIL, "password": "password-dari-admin"}
    assert client.post("/login", data=login).status_code == 401
    login["password"] = CREATOR_PASSWORD
    assert client.post("/login", data=login).status_code == 200
