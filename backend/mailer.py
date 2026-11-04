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


def send_mail(to: str, subject: str, html: str, text: str) -> bool:
    """True kalau terkirim, False kalau SMTP belum dikonfigurasi (mode dev).

    Error SMTP (koneksi, login, penolakan alamat) diteruskan ke pemanggil.
    """
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        # flush: di PM2 stdout ter-buffer, padahal link di sini dibutuhkan segera.
        print(
            f"[MAIL] SMTP_HOST kosong, email tidak dikirim.\n"
            f"To: {to}\nSubject: {subject}\n\n{text}",
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

    with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if user:
            smtp.login(user, os.getenv("SMTP_PASS", ""))
        smtp.send_message(msg)
    return True
