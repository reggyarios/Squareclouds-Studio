from pathlib import Path
import argparse
import sqlite3


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "backend" / "squareclouds.db"
UPLOADS_DIR = PROJECT_ROOT / "backend" / "uploads"


# ============================================================
# ARGUMENTS
# ============================================================

parser = argparse.ArgumentParser(
    description="Find and optionally delete orphaned upload files."
)

parser.add_argument(
    "--delete",
    action="store_true",
    help="Actually delete orphaned files. Without this flag, only preview."
)

args = parser.parse_args()


# ============================================================
# DATABASE
# ============================================================

def get_database_files():
    """
    Find strings in the SQLite database that look like
    references to files inside the uploads directory.
    """

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%';
        """)

        tables = [row[0] for row in cursor.fetchall()]

        referenced_files = set()

        for table in tables:
            cursor.execute(f'PRAGMA table_info("{table}")')
            columns = cursor.fetchall()

            for column in columns:
                column_name = column[1]

                # Only inspect text-like columns.
                # We intentionally don't assume specific model names.
                try:
                    cursor.execute(
                        f'''
                        SELECT "{column_name}"
                        FROM "{table}"
                        WHERE "{column_name}" IS NOT NULL
                        '''
                    )

                    for row in cursor.fetchall():
                        value = row[0]

                        if not isinstance(value, str):
                            continue

                        value = value.strip()

                        if not value:
                            continue

                        # Check whether this value refers to an
                        # upload file.
                        if is_upload_reference(value):
                            referenced_files.add(value)

                except sqlite3.Error:
                    # Ignore columns that cannot safely be queried.
                    continue

        return referenced_files

    finally:
        connection.close()


# ============================================================
# FILE REFERENCE DETECTION
# ============================================================

def is_upload_reference(value: str) -> bool:
    """
    Determine whether a database value appears to reference
    a file inside the uploads directory.
    """

    normalized = value.replace("\\", "/")

    # Common patterns used by web applications.
    patterns = [
        "uploads/",
        "/uploads/",
        "uploads\\",
        "/uploads\\",
    ]

    if any(pattern in normalized.lower() for pattern in patterns):
        return True

    return False


def normalize_reference(value: str) -> str | None:
    """
    Convert a database file reference into a relative path
    inside backend/uploads.
    """

    normalized = value.replace("\\", "/")

    lower = normalized.lower()

    markers = [
        "uploads/",
    ]

    for marker in markers:
        index = lower.find(marker)

        if index != -1:
            relative = normalized[index + len(marker):]

            relative = relative.lstrip("/")

            if relative:
                return relative

    return None


# ============================================================
# GET REFERENCED FILES
# ============================================================

def get_referenced_upload_paths():
    raw_references = get_database_files()

    referenced_paths = set()

    for reference in raw_references:
        relative_path = normalize_reference(reference)

        if relative_path:
            referenced_paths.add(relative_path)

    return referenced_paths


# ============================================================
# GET ACTUAL FILES
# ============================================================

def get_upload_files():
    if not UPLOADS_DIR.exists():
        raise FileNotFoundError(
            f"Uploads directory not found: {UPLOADS_DIR}"
        )

    files = set()

    for path in UPLOADS_DIR.rglob("*"):
        if path.is_file():
            relative = path.relative_to(UPLOADS_DIR)

            files.add(
                relative.as_posix()
            )

    return files


# ============================================================
# CLEANUP
# ============================================================

def cleanup():
    print("=" * 60)
    print("UPLOAD CLEANUP")
    print("=" * 60)

    print(f"Database : {DATABASE_PATH}")
    print(f"Uploads  : {UPLOADS_DIR}")
    print()

    referenced_files = get_referenced_upload_paths()
    upload_files = get_upload_files()

    orphan_files = upload_files - referenced_files

    print(f"Referenced files : {len(referenced_files)}")
    print(f"Upload files     : {len(upload_files)}")
    print(f"Orphan files     : {len(orphan_files)}")
    print()

    if not orphan_files:
        print("No orphan files found.")
        return

    print("Orphan files:")
    print("-" * 60)

    total_size = 0

    for relative_path in sorted(orphan_files):
        full_path = UPLOADS_DIR / relative_path

        try:
            size = full_path.stat().st_size
            total_size += size
        except OSError:
            size = 0

        print(
            f"{relative_path} "
            f"({format_size(size)})"
        )

    print("-" * 60)
    print(f"Total orphan size: {format_size(total_size)}")
    print()

    # ========================================================
    # DRY RUN
    # ========================================================

    if not args.delete:
        print("DRY RUN")
        print("Nothing was deleted.")
        print()
        print(
            "To actually delete these files, run:"
        )
        print()
        print(
            "python backend/scripts/cleanup_uploads.py --delete"
        )

        return

    # ========================================================
    # DELETE
    # ========================================================

    print("DELETE MODE")
    print("Deleting orphan files...")
    print()

    deleted = 0
    failed = 0

    for relative_path in sorted(orphan_files):
        full_path = UPLOADS_DIR / relative_path

        try:
            full_path.unlink()

            print(f"Deleted: {relative_path}")

            deleted += 1

        except OSError as error:
            print(
                f"FAILED: {relative_path} "
                f"({error})"
            )

            failed += 1

    print()
    print("=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)

    print(f"Deleted : {deleted}")
    print(f"Failed  : {failed}")


# ============================================================
# FORMAT SIZE
# ============================================================

def format_size(size: int) -> str:
    units = [
        "B",
        "KB",
        "MB",
        "GB",
    ]

    value = float(size)

    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} TB"


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    cleanup()