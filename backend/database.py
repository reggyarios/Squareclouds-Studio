from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./squareclouds.db"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,

    # SQLite connection hanya boleh digunakan oleh thread
    # yang membuatnya secara default.
    # FastAPI bisa menggunakan beberapa thread,
    # jadi kita disable restriction ini.
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },

    # Untuk SQLite + FastAPI, connection pool sederhana
    # sudah cukup untuk kebutuhan portal saat ini.
    pool_pre_ping=True,
)


# ============================================================
# SQLITE PERFORMANCE / CONCURRENCY
# ============================================================

@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()

    # WAL = Write-Ahead Logging
    #
    # Keuntungan:
    # - Reader tidak terlalu terganggu ketika ada writer.
    # - Read/write concurrency lebih baik.
    # - Cocok untuk aplikasi web dengan SQLite.
    cursor.execute("PRAGMA journal_mode=WAL")

    # Menunggu sampai 30 detik jika database sedang dikunci.
    # Ini menjadi lapisan tambahan selain timeout pada connection.
    cursor.execute("PRAGMA busy_timeout=30000")

    # Foreign key harus diaktifkan secara eksplisit di SQLite.
    cursor.execute("PRAGMA foreign_keys=ON")

    # Sinkronisasi NORMAL memberikan performa lebih baik
    # dibanding FULL dengan durability yang masih baik
    # ketika menggunakan WAL.
    cursor.execute("PRAGMA synchronous=NORMAL")

    cursor.close()


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# BASE MODEL
# ============================================================

Base = declarative_base()


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables():
    # Import di dalam function untuk mencegah circular import.
    import models

    Base.metadata.create_all(bind=engine)