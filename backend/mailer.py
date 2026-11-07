"""Kirim email lewat SMTP + STARTTLS.

Konfigurasi dari backend/.env (lihat .env.example):
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, MAIL_FROM

SMTP_HOST kosong = mode dev: email tidak dikirim, hanya dicetak ke log.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SMTP_TIMEOUT_SECONDS = 20


def send_mail(
    to: str,
    subject: str,
    html: str,
    text: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    """True kalau terkirim, False kalau SMTP belum dikonfigurasi (mode dev).

    attachments: [(nama file, isi, mime type)], mis.
    ("slip.pdf", b"%PDF...", "application/pdf").

    Error SMTP (koneksi, login, penolakan alamat) diteruskan ke pemanggil.
    """
    attachments = attachments or []
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        listed = "".join(f"\nLampiran: {name} ({len(data)} byte)" for name, data, _ in attachments)
        # flush: di PM2 stdout ter-buffer, padahal link di sini dibutuhkan segera.
        print(
            f"[MAIL] SMTP_HOST kosong, email tidak dikirim.\n"
            f"To: {to}\nSubject: {subject}{listed}\n\n{text}",
            flush=True,
        )
        return False

    user = os.getenv("SMTP_USER", "").strip()
    port = int(os.getenv("SMTP_PORT", "").strip() or 587)

    msg = EmailMessage()
    msg["From"] = os.getenv("MAIL_FROM", "").strip() or user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    # Lampiran pertama mengubah pesan jadi multipart/mixed: [alternative(teks,
    # html), lampiran...].
    for name, data, mime_type in attachments:
        maintype, _, subtype = mime_type.partition("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)

    with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if user:
            smtp.login(user, os.getenv("SMTP_PASS", ""))
        smtp.send_message(msg)
    return True
