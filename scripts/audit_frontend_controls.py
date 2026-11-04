"""Audit frontend controls, links, and handlers for anti-patterns.

Ensures no empty onClick handlers, no dead href="#" links, and no placeholder UI data.
"""

import os
import re
import sys
from pathlib import Path


def audit_frontend() -> int:
    root_dir = Path(__file__).resolve().parents[1] / "frontend" / "src"
    violations: list[str] = []

    bad_href_pattern = re.compile(r'href\s*=\s*["\'](#|javascript:void\(0\)|)["\']')
    empty_onclick_pattern = re.compile(r'onClick\s*=\s*\{\s*\(\s*\)\s*=>\s*(\{\s*\}|undefined|null|void\s*0)\s*\}')
    todo_comment_pattern = re.compile(r'//\s*TODO|{\s*/\*\s*TODO')

    for path in root_dir.rglob("*.tsx"):
        rel_path = path.relative_to(root_dir.parent.parent)
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                if bad_href_pattern.search(clean_line):
                    violations.append(f"[DEAD LINK] {rel_path}:{idx} -> {clean_line}")
                if empty_onclick_pattern.search(clean_line):
                    violations.append(f"[EMPTY HANDLER] {rel_path}:{idx} -> {clean_line}")
                if todo_comment_pattern.search(clean_line):
                    violations.append(f"[TODO STUB] {rel_path}:{idx} -> {clean_line}")

    if violations:
        print(f"FAILED: Found {len(violations)} frontend control violations:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("PASSED: All frontend controls, links, and handlers are properly wired. No anti-patterns found.")
    return 0


if __name__ == "__main__":
    sys.exit(audit_frontend())
