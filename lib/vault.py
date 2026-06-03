"""Vault discovery, validation, and repair for obsidian-skill.

Cross-platform search for Obsidian vaults, multi-tier validation,
and automatic repair when a configured vault path goes stale.
"""

import os
import platform
from pathlib import Path
from typing import Any


# ── Constants ────────────────────────────────────────────────────────────────────

# Required checks — all must pass for a vault to be considered valid.
REQUIRED_CHECKS = [
    "path_exists",
    "is_directory",
    "dot_obsidian_exists",
    "readable",
    "writable",
]

# Optional checks — failure generates a warning but does not invalidate.
OPTIONAL_CHECKS = [
    "obsidian_json_exists",
    "has_markdown",
]

# Platform-specific search roots for vault discovery.
SEARCH_ROOTS: dict[str, list[str]] = {
    "Darwin": [
        "~/Documents",
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents",
    ],
    "Linux": [
        "~/Documents",
    ],
    "Windows": [
        "~/Documents",
        "~/AppData/Roaming/Obsidian",
    ],
}


# ── Validation ──────────────────────────────────────────────────────────────────

def validate_vault(path: str | Path) -> dict[str, Any]:
    """Run multi-tier validation on a vault path.

    Returns:
        {
            "valid": bool,            # All required checks passed
            "path": str,              # Resolved absolute path
            "name": str,              # Directory name (vault name)
            "checks": {               # Per-check results
                "path_exists": bool,
                "is_directory": bool,
                "dot_obsidian_exists": bool,
                "readable": bool,
                "writable": bool,
                "obsidian_json_exists": bool,
                "has_markdown": bool,
            },
            "warnings": [str],        # List of non-blocking issues
        }

    A vault is valid when all REQUIRED_CHECKS pass.
    OPTIONAL_CHECKS failures produce warnings.
    """
    p = Path(path).expanduser().resolve()
    name = p.name
    checks: dict[str, bool] = {}
    warnings: list[str] = []

    # path_exists
    checks["path_exists"] = p.exists()

    # is_directory
    checks["is_directory"] = p.is_dir() if checks["path_exists"] else False

    # dot_obsidian_exists
    checks["dot_obsidian_exists"] = (p / ".obsidian").is_dir() if checks["is_directory"] else False

    # readable
    checks["readable"] = os.access(p, os.R_OK) if checks["path_exists"] else False

    # writable
    checks["writable"] = os.access(p, os.W_OK) if checks["path_exists"] else False

    # Optional: obsidian.json
    checks["obsidian_json_exists"] = (p / ".obsidian" / "obsidian.json").is_file() if checks["dot_obsidian_exists"] else False
    if checks["dot_obsidian_exists"] and not checks["obsidian_json_exists"]:
        warnings.append("obsidian.json not found — may be an older vault or custom setup")

    # Optional: has at least one .md file
    if checks["is_directory"]:
        has_md = any(p.rglob("*.md"))
        checks["has_markdown"] = has_md
        if not has_md:
            warnings.append("No .md files found — vault may be empty")
    else:
        checks["has_markdown"] = False

    # Determine overall validity
    valid = all(checks.get(k, False) for k in REQUIRED_CHECKS)

    return {
        "valid": valid,
        "path": str(p),
        "name": name,
        "checks": checks,
        "warnings": warnings,
    }


def format_validation_report(result: dict[str, Any]) -> str:
    """Render a validation result as a human-readable text report."""
    lines = [
        f"Vault: {result['path']}",
        f"Valid: {'✅ Yes' if result['valid'] else '❌ No'}",
        "",
    ]

    for check in REQUIRED_CHECKS:
        passed = result["checks"].get(check, False)
        icon = "✅" if passed else "❌"
        lines.append(f"  {icon} {check} (required)")

    for check in OPTIONAL_CHECKS:
        passed = result["checks"].get(check, False)
        icon = "✅" if passed else "⚠️"
        lines.append(f"  {icon} {check} (optional)")

    if result["warnings"]:
        lines.append("")
        for w in result["warnings"]:
            lines.append(f"  ⚠️  {w}")

    if not result["valid"]:
        lines.append("")
        lines.append("Action: Vault is not usable. Run 'obsidian-skill repair' or 'obsidian-skill init'.")

    return "\n".join(lines)


# ── Search ──────────────────────────────────────────────────────────────────────

def _get_search_roots() -> list[Path]:
    """Return platform-specific search root directories, resolved."""
    system = platform.system()
    patterns = SEARCH_ROOTS.get(system, SEARCH_ROOTS["Linux"])
    roots: list[Path] = []
    for pattern in patterns:
        p = Path(pattern).expanduser().resolve()
        if p.exists():
            roots.append(p)
    return roots


def search_vaults(max_depth: int = 3) -> list[dict[str, Any]]:
    """Search the filesystem for Obsidian vaults.

    Scans platform-specific root directories, walking up to max_depth levels,
    looking for any directory that contains a .obsidian subdirectory.

    Returns a list of validated vault dicts (same format as validate_vault).
    """
    roots = _get_search_roots()
    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    for root in roots:
        for dirpath, dirnames, _ in os.walk(root):
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

                result = validate_vault(dirpath)
                results.append(result)

    return results


def search_vaults_simple() -> list[str]:
    """Return a flat list of valid vault paths for use in selection UIs."""
    vaults = search_vaults()
    return [v["path"] for v in vaults if v["valid"]]


# ── Repair ──────────────────────────────────────────────────────────────────────

def repair_vault(configured_path: str, discovered_vaults: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Attempt to repair a stale vault path.

    Strategy:
        1. Check if configured path still works — if so, no repair needed.
        2. Search for discovered vaults from state that match the old vault name.
        3. Run a fresh search and look for name matches.
        4. Return the best candidate for user confirmation.

    Returns:
        {
            "repaired": bool,
            "old_path": str,
            "new_path": str | None,
            "candidates": [str],       # All found alternatives
            "message": str,
        }
    """
    result = validate_vault(configured_path)
    if result["valid"]:
        return {
            "repaired": False,
            "old_path": configured_path,
            "new_path": None,
            "candidates": [],
            "message": "Vault is already valid — no repair needed.",
        }

    old_name = Path(configured_path).name
    candidates: list[str] = []

    # Check discovered vaults from state first (fast)
    if discovered_vaults:
        for dv in discovered_vaults:
            if dv.get("name") == old_name and dv.get("valid"):
                dv_path = dv["path"]
                v = validate_vault(dv_path)
                if v["valid"]:
                    candidates.append(dv_path)

    # Fall back to fresh search
    if not candidates:
        fresh = search_vaults()
        for vault in fresh:
            if vault["name"] == old_name and vault["valid"]:
                if vault["path"] not in candidates:
                    candidates.append(vault["path"])

    if candidates:
        return {
            "repaired": True,
            "old_path": configured_path,
            "new_path": candidates[0],
            "candidates": candidates,
            "message": f"Found {len(candidates)} candidate(s) matching vault name '{old_name}'.",
        }

    # No candidates — list all available vaults
    all_vaults = search_vaults_simple()
    return {
        "repaired": False,
        "old_path": configured_path,
        "new_path": None,
        "candidates": all_vaults,
        "message": f"Original vault '{configured_path}' not found. {len(all_vaults)} other vault(s) available.",
    }


# ── Doctor check ────────────────────────────────────────────────────────────────

def doctor_check() -> dict[str, Any]:
    """Return a diagnostic snapshot for the vault subsystem."""
    from lib.config import get_vault_path

    vault_path = get_vault_path()
    result: dict[str, Any] = {
        "vault_configured": vault_path is not None,
    }

    if vault_path:
        result["validation"] = validate_vault(vault_path)
    else:
        result["validation"] = None

    result["all_vaults_found"] = search_vaults_simple()
    return result
