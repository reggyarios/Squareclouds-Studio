from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"


# Files/directories that should not be scanned
IGNORED_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".git",
}


# Patterns that commonly indicate database deletion
DELETE_PATTERNS = [
    r"\bdb\.delete\s*\(",
    r"\bsession\.delete\s*\(",
    r"\bsession\.execute\s*\(",
    r"\.delete\s*\(",
    r"\bquery\.delete\s*\(",
]


def should_ignore(path: Path) -> bool:
    return any(
        part in IGNORED_DIRS
        for part in path.parts
    )


def find_delete_operations():
    results = []

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

            for pattern in DELETE_PATTERNS:

                if re.search(pattern, line):

                    results.append({
                        "file": path.relative_to(PROJECT_ROOT),
                        "line": line_number,
                        "code": line.strip(),
                    })

                    break

    return results


def main():
    print("=" * 70)
    print("DATABASE DELETE OPERATION AUDIT")
    print("=" * 70)
    print()

    results = find_delete_operations()

    if not results:
        print("No delete operations found.")
        return

    print(
        f"Found {len(results)} possible delete operations."
    )
    print()

    for index, result in enumerate(results, start=1):

        print(f"[{index}]")
        print(f"File : {result['file']}")
        print(f"Line : {result['line']}")
        print(f"Code : {result['code']}")
        print()

    print("=" * 70)
    print("IMPORTANT")
    print("=" * 70)
    print()
    print(
        "These are potential database deletion operations."
    )
    print(
        "Review each one before adding file cleanup."
    )


if __name__ == "__main__":
    main()