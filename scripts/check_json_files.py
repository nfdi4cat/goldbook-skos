"""List Gold Book term files in a directory that are not valid term records.

Usage: python -I scripts/check_json_files.py <directory>

Checks every *.json file in the directory (not recursive). A file passes if
it parses as JSON, is an object whose only key is "term", the "term" object
has all REQUIRED_TERM_FIELDS, and "term.code" matches the file name, either
"<code>.json" or "goldbook_term_<code>.json".

Prints one line per failing file with the reason, then a summary. Exits with
status 1 if any file fails.
"""

import json
import sys
from pathlib import Path

SNIPPET_LENGTH = 60
FILENAME_PREFIX = "goldbook_term_"
REQUIRED_TERM_FIELDS = frozenset(
    {
        "id",
        "title",
        "longtitle",
        "doi",
        "code",
        "status",
        "definitions",
        "altoutputs",
        "citation",
        "license",
        "collection",
        "disclaimer",
        "accessed",
    }
)


def check_file(path: Path) -> str | None:
    """Return an error description if the file is not a valid term record, else None."""
    data = path.read_bytes()
    if not data.strip():
        return "empty file"
    try:
        # json.loads on bytes detects UTF-8/16/32 itself.
        record = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        snippet = data[:SNIPPET_LENGTH].decode("utf-8", errors="replace")
        return f"not JSON: {exc} | starts with: {snippet!r}"

    if not isinstance(record, dict) or list(record) != ["term"]:
        top = sorted(record) if isinstance(record, dict) else type(record).__name__
        return f'top level is not an object with the single key "term": {top}'

    term = record["term"]
    if not isinstance(term, dict):
        return f'"term" is a {type(term).__name__}, not an object'

    missing = REQUIRED_TERM_FIELDS - term.keys()
    if missing:
        return f'"term" lacks fields: {sorted(missing)}'

    code = str(term["code"])
    if path.stem not in (code, FILENAME_PREFIX + code):
        return f'"term.code" {code!r} does not match the file name'
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    directory = Path(sys.argv[1])
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        return 2

    files = sorted(directory.glob("*.json"))
    invalid = []
    for path in files:
        error = check_file(path)
        if error is not None:
            invalid.append(path)
            print(f"{path.name}: {error}")

    print(f"\nChecked {len(files)} files, {len(invalid)} not valid term records.")
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
