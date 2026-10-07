import os
import sqlite3
from datetime import datetime
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = BASE_DIR / "squareclouds.db"

BACKUP_DIR = BASE_DIR.parent / "backups" / "database"

MAX_BACKUPS = 30


# ============================================================
# HELPERS
# ============================================================

def format_size(size_bytes: int) -> str:
    """Convert bytes to readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"

    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"

    if size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"

    return f"{size_bytes / (1024 ** 3):.2f} GB"


def verify_backup(backup_path: Path) -> bool:
    """
    Verify that the backup file is a valid SQLite database.
    """

    try:
        connection = sqlite3.connect(
            f"file:{backup_path}?mode=ro",
            uri=True
        )

        cursor = connection.cursor()

        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()

        connection.close()

        return result is not None and result[0] == "ok"

    except Exception as error:
        print(f"Backup verification failed: {error}")
        return False


def cleanup_old_backups():
    """
    Keep only the newest MAX_BACKUPS files.
    """

    backups = sorted(
        BACKUP_DIR.glob("squareclouds_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if len(backups) <= MAX_BACKUPS:
        return

    old_backups = backups[MAX_BACKUPS:]

    print()
    print("Cleaning old backups...")

    for backup in old_backups:
        try:
            backup.unlink()
            print(f"Deleted: {backup.name}")
        except Exception as error:
            print(
                f"Failed to delete {backup.name}: {error}"
            )


# ============================================================
# MAIN BACKUP
# ============================================================

def create_backup():

    print("=" * 60)
    print("SQUARECLOUDS DATABASE BACKUP")
    print("=" * 60)

    print(f"Database : {DATABASE_PATH}")
    print(f"Backup   : {BACKUP_DIR}")
    print()

    # --------------------------------------------------------
    # Check database
    # --------------------------------------------------------

    if not DATABASE_PATH.exists():
        print("ERROR: Database file does not exist.")
        return False

    # --------------------------------------------------------
    # Create backup directory
    # --------------------------------------------------------

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Generate filename
    # --------------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    backup_path = (
        BACKUP_DIR /
        f"squareclouds_{timestamp}.db"
    )

    # --------------------------------------------------------
    # SQLite Online Backup
    # --------------------------------------------------------

    source = None
    destination = None

    try:

        source = sqlite3.connect(
            DATABASE_PATH
        )

        destination = sqlite3.connect(
            backup_path
        )

        print("Creating backup...")

        source.backup(destination)

        destination.commit()

        print("Backup created successfully.")

    except Exception as error:

        print()
        print("ERROR: Backup failed.")
        print(error)

        if backup_path.exists():
            backup_path.unlink()

        return False

    finally:

        if destination:
            destination.close()

        if source:
            source.close()

    # --------------------------------------------------------
    # Check backup exists
    # --------------------------------------------------------

    if not backup_path.exists():

        print("ERROR: Backup file was not created.")

        return False

    # --------------------------------------------------------
    # Check backup size
    # --------------------------------------------------------

    backup_size = backup_path.stat().st_size

    print(
        f"Backup size: {format_size(backup_size)}"
    )

    if backup_size == 0:

        print(
            "ERROR: Backup file is empty."
        )

        backup_path.unlink()

        return False

    # --------------------------------------------------------
    # Verify SQLite integrity
    # --------------------------------------------------------

    print("Verifying backup...")

    if not verify_backup(backup_path):

        print()
        print(
            "ERROR: Backup integrity check failed."
        )

        backup_path.unlink()

        return False

    print(
        "Backup integrity: OK"
    )

    # --------------------------------------------------------
    # Cleanup old backups
    # --------------------------------------------------------

    cleanup_old_backups()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    remaining_backups = list(
        BACKUP_DIR.glob("squareclouds_*.db")
    )

    print()
    print("=" * 60)
    print("BACKUP COMPLETED")
    print("=" * 60)

    print(f"File      : {backup_path}")
    print(f"Size      : {format_size(backup_size)}")
    print(
        f"Backups   : {len(remaining_backups)} / {MAX_BACKUPS}"
    )

    return True


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = create_backup()

    if not success:
        raise SystemExit(1)