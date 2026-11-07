"""Helpers for detecting and reading unified diffs."""
import re
from dataclasses import dataclass

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass(frozen=True)
class AddedLine:
    file: str
    line: int
    text: str


def is_unified_diff(text: str) -> bool:
    lines = text.splitlines()
    has_hunk = any(HUNK_RE.match(l) for l in lines)
    has_header = any(l.startswith("+++ ") for l in lines) and any(l.startswith("--- ") for l in lines)
    return has_hunk and has_header


def extract_added_lines(diff: str) -> list[AddedLine]:
    """Return every added line with its new-file line number."""
    added: list[AddedLine] = []
    current_file = "unknown"
    new_line = 0
    in_hunk = False
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].strip()
            current_file = path[2:] if path.startswith("b/") else path
            in_hunk = False
            continue
        if raw.startswith("--- "):
            in_hunk = False
            continue
        m = HUNK_RE.match(raw)
        if m:
            new_line = int(m.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith("+"):
            added.append(AddedLine(current_file, new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-"):
            continue
        else:
            new_line += 1
    return added
