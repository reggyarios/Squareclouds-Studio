"""Manajemen kreator oleh admin."""
import auth
import models
from database import SessionLocal

CREATOR_EMAIL = "creator@example.com"
CREATOR_PASSWORD = "creator-password"


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
