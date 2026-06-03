#!/usr/bin/env python3
"""Search for Obsidian vaults on this system. Outputs JSON array.

Usage:
    python scripts/helper.py          # human-readable
    python scripts/helper.py --json   # JSON output (for AI to parse)
"""

import json
import os
import platform
import sys
from pathlib import Path

SEARCH_ROOTS = {
    "Darwin": [
        "~/Documents",
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents",
    ],
    "Linux": ["~/Documents"],
    "Windows": ["~/Documents", "~/AppData/Roaming/Obsidian"],
}


def find_vaults(max_depth: int = 3) -> list[dict]:
    system = platform.system()
    roots = SEARCH_ROOTS.get(system, SEARCH_ROOTS["Linux"])
    seen = set()
    results = []

    for pattern in roots:
        root = Path(pattern).expanduser().resolve()
        if not root.exists():
            continue
        for dirpath, dirnames, _ in os.walk(root, onerror=lambda e: None):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth > max_depth:
                dirnames.clear()
                continue
            obsidian_dir = Path(dirpath) / ".obsidian"
            if obsidian_dir.is_dir():
                resolved = str(Path(dirpath).resolve())
                if resolved in seen:
                    continue
                seen.add(resolved)
                p = Path(dirpath)
                results.append({
                    "path": resolved,
                    "name": p.name,
                })
    return results


def main():
    vaults = find_vaults()
    if "--json" in sys.argv:
        json.dump(vaults, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        if not vaults:
            print("No Obsidian vaults found.")
        for v in vaults:
            print(f"  {v['name']:24s} {v['path']}")


if __name__ == "__main__":
    main()
