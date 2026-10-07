from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOADS_DIR = (PROJECT_ROOT / "uploads").resolve()


def extract_upload_path(file_path: str | None) -> str | None:
    """
    Convert a stored upload URL/path into a relative path.

    Supported examples:

        /uploads/abc.webp
        uploads/abc.webp
        abc.webp
        https://squarecloudsmc.com/uploads/abc.webp
        https://squarecloudsmc.com/uploads/abc.webp

    Returns:
        Relative path inside uploads directory.
    """

    if not file_path:
        return None

    value = str(file_path).strip()

    if not value:
        return None

    # Handle full URLs.
    parsed = urlparse(value)

    if parsed.scheme and parsed.netloc:
        value = parsed.path

    # Normalize Windows separators.
    value = value.replace("\\", "/")

    # Extract everything after /uploads/
    if "/uploads/" in value:
        value = value.split("/uploads/", 1)[1]

    elif value.startswith("uploads/"):
        value = value[len("uploads/"):]

    else:
        value = value.lstrip("/")

    return value or None


def get_upload_target(file_path: str | None) -> Path | None:
    """
    Convert a stored file URL/path into a safe filesystem path.

    Prevents path traversal such as:

        ../../important-file
    """

    relative_path = extract_upload_path(file_path)

    if not relative_path:
        return None

    target = (UPLOADS_DIR / relative_path).resolve()

    try:
        target.relative_to(UPLOADS_DIR)
    except ValueError:
        raise ValueError(
            f"Invalid upload path: {file_path}"
        )

    return target


def delete_upload(file_path: str | None) -> bool:
    """
    Safely delete one uploaded file.

    Returns:
        True  -> file existed and was deleted
        False -> file did not exist / empty path
    """

    target = get_upload_target(file_path)

    if target is None:
        return False

    if not target.is_file():
        return False

    target.unlink()

    return True


def delete_uploads(file_paths: list[str | None]) -> int:
    """
    Delete multiple uploaded files.

    Returns:
        Number of files successfully deleted.
    """

    deleted = 0

    for file_path in file_paths:
        if delete_upload(file_path):
            deleted += 1

    return deleted