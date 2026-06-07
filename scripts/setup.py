#!/usr/bin/env python3
"""First-time setup wizard for agent-knowledge skill.

Guides the user through vault discovery, validation, preference collection,
and bootstraps the vault directory structure.

Usage:
    python scripts/setup.py                    # interactive
    python scripts/setup.py --path /vault/dir  # non-interactive with explicit path
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "vault_config.json"

SEARCH_ROOTS = {
    "Darwin": [
        "~/Documents",
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents",
    ],
    "Linux": ["~/Documents"],
    "Windows": ["~/Documents", "~/AppData/Roaming/Obsidian"],
}

VAULT_SUBDIRS = [
    "Daily",
    "Sessions",
    "Projects",
    "Knowledge",
    "Meta",
]


def find_vaults(max_depth: int = 3) -> list[dict]:
    """Scan common locations for Obsidian vaults."""
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
                results.append({"path": resolved, "name": p.name})
    return results


def validate_vault(path: str) -> dict:
    """Check whether a path is a usable Obsidian vault. Returns a validation report."""
    p = Path(path).expanduser().resolve()
    checks = {}
    warnings = []

    checks["path_exists"] = p.exists()
    checks["is_directory"] = p.is_dir() if checks["path_exists"] else False
    checks["dot_obsidian_exists"] = (
        (p / ".obsidian").is_dir() if checks["is_directory"] else False
    )
    checks["readable"] = os.access(p, os.R_OK) if checks["path_exists"] else False
    checks["writable"] = os.access(p, os.W_OK) if checks["path_exists"] else False

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


def bootstrap_vault(vault_path: str) -> list[str]:
    """Create recommended subdirectories inside the vault. Returns list of created dirs."""
    created = []
    for subdir in VAULT_SUBDIRS:
        target = Path(vault_path) / subdir
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
    return created


def collect_preferences() -> dict:
    """Interactive preference collection. Falls back to defaults if not interactive."""
    return {
        "date_format": "YYYY-MM-DD",
        "auto_link": True,
        "graph_enabled": True,
        "note_lang": "zh",
    }


def write_config(vault_path: str, preferences: dict | None = None) -> Path:
    """Write vault_config.json. Returns path to config file."""
    if preferences is None:
        preferences = collect_preferences()

    config = {
        "vault_path": str(Path(vault_path).expanduser().resolve()),
        "default_project": None,
        **preferences,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return CONFIG_FILE


def main():
    vault_path = None

    # Parse --path flag
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--path" and i + 1 < len(sys.argv[1:]):
            vault_path = sys.argv[i + 2]
            break
        if arg.startswith("--path="):
            vault_path = arg.split("=", 1)[1]
            break

    # JSON output mode — used by AI to discover vaults
    if "--json" in sys.argv:
        vaults = find_vaults()
        json.dump(vaults, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    # Discovery mode — list found vaults
    if "--discover" in sys.argv:
        vaults = find_vaults()
        if not vaults:
            print("No Obsidian vaults found automatically.")
            print("Use --path <path> to specify a vault path.")
            return
        print("Found vaults:")
        for v in vaults:
            print(f"  {v['name']:24s} {v['path']}")
        return

    # Validate mode
    if vault_path and "--validate" in sys.argv:
        result = validate_vault(vault_path)
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
        sys.exit(0 if result["valid"] else 1)

    # Setup mode — requires a path
    if not vault_path:
        # Try auto-discovery first
        vaults = find_vaults()
        if vaults:
            print("Found Obsidian vaults:")
            for i, v in enumerate(vaults):
                print(f"  [{i}] {v['name']:24s} {v['path']}")
            print()
            print("Run with --path <path> to select one, or re-run to pick interactively.")
            # Output JSON so the AI can parse and present choices
            if len(vaults) == 1:
                vault_path = vaults[0]["path"]
                print(f"Auto-selecting only vault: {vault_path}")
            else:
                print("Multiple vaults found. Use --path to specify.")
                sys.exit(0)
        else:
            print("No Obsidian vaults found automatically.")
            print("Run: python scripts/setup.py --path /path/to/your/vault")
            sys.exit(1)

    # Validate the path
    result = validate_vault(vault_path)
    if not result["valid"]:
        print(f"Invalid vault path: {vault_path}")
        for check, passed in result["checks"].items():
            if not passed:
                print(f"  ✗ {check}")
        for w in result["warnings"]:
            print(f"  ⚠ {w}")
        sys.exit(1)

    # Bootstrap vault structure
    created = bootstrap_vault(vault_path)
    if created:
        print("Created vault directories:")
        for d in created:
            print(f"  + {d}")

    # Write config
    config_path = write_config(vault_path)
    print(f"Config written: {config_path}")
    print("Setup complete. agent-knowledge skill is ready.")

    # Output final config as JSON for AI consumption
    print()
    json.dump({"status": "ready", "config_path": str(config_path), "vault_path": str(Path(vault_path).expanduser().resolve())}, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
