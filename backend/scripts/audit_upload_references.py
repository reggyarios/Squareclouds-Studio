from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"


IGNORED_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".git",
}


IMAGE_KEYWORDS = [
    "image",
    "img",
    "photo",
    "avatar",
    "thumbnail",
    "thumb",
    "logo",
    "cover",
    "banner",
    "icon",
    "file",
    "path",
    "url",
]


def should_ignore(path: Path) -> bool:
    return any(
        part in IGNORED_DIRS
        for part in path.parts
    )


def main():
    print("=" * 70)
    print("UPLOAD / IMAGE REFERENCE AUDIT")
    print("=" * 70)
    print()

    found = []

    for path in BACKEND_DIR.rglob("*.py"):

        if should_ignore(path):
            continue

        try:
            content = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        lines = content.splitlines()

        for line_number, line in enumerate(lines, start=1):

            stripped = line.strip()

            if not stripped:
                continue

            lower = stripped.lower()

            # Only report likely image/file fields.
            if not any(
                keyword in lower
                for keyword in IMAGE_KEYWORDS
            ):
                continue

            # SQLAlchemy-style columns
            if (
                "column(" in lower
                or "mapped[" in lower
                or "image" in lower
                or "thumbnail" in lower
                or "avatar" in lower
                or "logo" in lower
                or "file" in lower
            ):
                found.append(
                    (
                        path.relative_to(PROJECT_ROOT),
                        line_number,
                        stripped,
                    )
                )

    if not found:
        print("No possible upload references found.")
        return

    for index, (file, line, code) in enumerate(
        found,
        start=1,
    ):
        print(f"[{index}]")
        print(f"File : {file}")
        print(f"Line : {line}")
        print(f"Code : {code}")
        print()

    print("=" * 70)
    print(f"Found {len(found)} possible references.")
    print("=" * 70)


if __name__ == "__main__":
    main()