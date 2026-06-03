#!/usr/bin/env python3
"""Validate whether a path is a usable Obsidian vault. Outputs JSON.

Usage:
    python scripts/validate_vault.py --path /path/to/vault
    python scripts/validate_vault.py --path ~/Documents/Obsidian
"""

import json
import os
import sys
from pathlib import Path


def validate(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    checks = {}
    warnings = []

    checks["path_exists"] = p.exists()
    checks["is_directory"] = p.is_dir() if checks["path_exists"] else False
    checks["dot_obsidian_exists"] = (p / ".obsidian").is_dir() if checks["is_directory"] else False
    checks["readable"] = os.access(p, os.R_OK) if checks["path_exists"] else False
    checks["writable"] = os.access(p, os.W_OK) if checks["path_exists"] else False

    # Optional checks
    if checks["dot_obsidian_exists"]:
        obsidian_json = p / ".obsidian" / "obsidian.json"
        if not obsidian_json.is_file():
            warnings.append("obsidian.json not found (older vault or custom setup)")
    if checks["is_directory"]:
        try:
            has_md = any(p.rglob("*.md"))
        except PermissionError:
            has_md = False
            warnings.append("Permission denied scanning for .md files")
        if not has_md:
            warnings.append("No .md files found — vault may be empty")

    required = ["path_exists", "is_directory", "dot_obsidian_exists", "readable", "writable"]
    valid = all(checks.get(k, False) for k in required)

    return {
        "valid": valid,
        "path": str(p),
        "name": p.name,
        "checks": checks,
        "warnings": warnings,
    }


def main():
    path = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--path" and i + 1 < len(sys.argv) - 1:
            path = sys.argv[i + 2]
            break
        if arg.startswith("--path="):
            path = arg.split("=", 1)[1]
            break

    if not path:
        print(json.dumps({"valid": False, "error": "No --path provided"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    result = validate(path)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
