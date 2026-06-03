"""Configuration and state file management for obsidian-skill.

Paths:
    CONFIG_DIR  = ~/.obsidian-skill/
    CONFIG_FILE = ~/.obsidian-skill/config.json
    STATE_FILE  = ~/.obsidian-skill/state.json
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


# ── Paths ────────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".obsidian-skill"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CONFIG_DIR / "state.json"


# ── Defaults ─────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG: dict[str, Any] = {
    "vault_path": "",
    "version": "1.0.0",
    "initialized_at": None,
    "agent": {
        "type": "claude-code",
        "version": "1.0.0",
    },
    "preferences": {
        "language": "zh",
        "auto_sync": True,
        "create_stubs": True,
    },
    "extensions": {},
}

DEFAULT_STATE: dict[str, Any] = {
    "version": "1.0.0",
    "last_sync": None,
    "discovered_vaults": [],
    "sync_stats": {
        "total_sessions": 0,
        "total_files_written": 0,
        "total_files_updated": 0,
        "total_qa_extracted": 0,
        "total_tech_entries": 0,
        "first_sync": None,
    },
    "extensions": {},
}


# ── Internal helpers ─────────────────────────────────────────────────────────────

def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict[str, Any] | None:
    """Read and parse a JSON file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write data as formatted JSON to path."""
    _ensure_dir()
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(path)  # atomic on POSIX


# ── Config API ──────────────────────────────────────────────────────────────────

def load_config() -> dict[str, Any]:
    """Load config, merging with defaults for any missing keys.

    Returns a dict — never fails. If file is missing or corrupt, returns defaults.
    """
    stored = _read_json(CONFIG_FILE)
    if stored is None:
        return dict(DEFAULT_CONFIG)
    # Merge: stored values take precedence, fill gaps from defaults
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: v for k, v in stored.items() if k in DEFAULT_CONFIG})
    return merged


def save_config(config: dict[str, Any]) -> None:
    """Persist config to disk."""
    _write_json(CONFIG_FILE, config)


def config_exists() -> bool:
    """Check whether config file exists on disk."""
    return CONFIG_FILE.exists()


def get_vault_path() -> str | None:
    """Return configured vault path, or None if not set."""
    cfg = load_config()
    path = cfg.get("vault_path", "")
    return path if path else None


def set_vault_path(path: str) -> None:
    """Update vault_path in config."""
    cfg = load_config()
    cfg["vault_path"] = path
    if cfg["initialized_at"] is None:
        cfg["initialized_at"] = datetime.now(timezone.utc).isoformat()
    save_config(cfg)


def get_preference(key: str, default: Any = None) -> Any:
    """Read a single preference by dotted key, e.g. 'language' or 'create_stubs'."""
    val = config_get(f"preferences.{key}")
    return val if val is not None else default


def set_preference(key: str, value: Any) -> None:
    """Set a single preference."""
    config_set(f"preferences.{key}", value)


def config_get(key: str) -> Any | None:
    """Generic dotted-key getter for config, e.g. 'agent.type' or 'preferences.language'."""
    cfg = load_config()
    parts = key.split(".")
    current: Any = cfg
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def config_set(key: str, value: Any) -> None:
    """Generic dotted-key setter for config."""
    cfg = load_config()
    parts = key.split(".")
    current = cfg
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value
    save_config(cfg)


def export_config() -> str:
    """Return the full config as a pretty-printed JSON string."""
    return json.dumps(load_config(), ensure_ascii=False, indent=2)


# ── State API ──────────────────────────────────────────────────────────────────

def load_state() -> dict[str, Any]:
    """Load state, merging with defaults for any missing keys."""
    stored = _read_json(STATE_FILE)
    if stored is None:
        return dict(DEFAULT_STATE)
    merged = dict(DEFAULT_STATE)
    merged.update({k: v for k, v in stored.items() if k in DEFAULT_STATE})
    return merged


def save_state(state: dict[str, Any]) -> None:
    """Persist state to disk."""
    _write_json(STATE_FILE, state)


def record_sync(session_id: str, project: str, files_written: int, files_updated: int) -> None:
    """Update state with the latest sync record and increment stats."""
    state = load_state()
    now = datetime.now(timezone.utc).isoformat()

    state["last_sync"] = {
        "timestamp": now,
        "session_id": session_id,
        "project": project,
        "files_written": files_written,
        "files_updated": files_updated,
    }

    stats = state["sync_stats"]
    stats["total_sessions"] += 1
    stats["total_files_written"] += files_written
    stats["total_files_updated"] += files_updated
    if stats["first_sync"] is None:
        stats["first_sync"] = now

    save_state(state)


def record_discovered_vault(vault_path: str, vault_name: str, valid: bool) -> None:
    """Add or update a discovered vault entry in state."""
    state = load_state()
    now = datetime.now(timezone.utc).isoformat()
    vaults: list[dict] = state["discovered_vaults"]

    for v in vaults:
        if v["path"] == vault_path:
            v["name"] = vault_name
            v["last_seen"] = now
            v["valid"] = valid
            break
    else:
        vaults.append({
            "path": vault_path,
            "name": vault_name,
            "last_seen": now,
            "valid": valid,
        })

    save_state(state)


def get_discovered_vaults(valid_only: bool = False) -> list[dict]:
    """Return discovered vaults from state, optionally filtering to valid ones."""
    state = load_state()
    vaults = state.get("discovered_vaults", [])
    if valid_only:
        return [v for v in vaults if v.get("valid")]
    return vaults


# ── Migrate API ─────────────────────────────────────────────────────────────────

MIGRATIONS: dict[str, Callable] = {}


def register_migration(from_version: str):
    """Decorator to register a migration function for a specific version upgrade."""
    def decorator(fn):
        MIGRATIONS[from_version] = fn
        return fn
    return decorator


def run_migrations() -> dict[str, Any]:
    """Apply any pending migrations to bring config to the current version."""
    cfg = load_config()
    current = cfg.get("version", "0.0.0")

    while current in MIGRATIONS:
        cfg = MIGRATIONS[current](cfg)
        current = cfg.get("version", "0.0.0")

    save_config(cfg)
    return cfg


# ── Doctor check ────────────────────────────────────────────────────────────────

def doctor_check() -> dict[str, Any]:
    """Return a diagnostic snapshot of the config/state system."""
    return {
        "config_dir_exists": CONFIG_DIR.exists(),
        "config_file_exists": CONFIG_FILE.exists(),
        "state_file_exists": STATE_FILE.exists(),
        "config_valid": _read_json(CONFIG_FILE) is not None if CONFIG_FILE.exists() else None,
        "state_valid": _read_json(STATE_FILE) is not None if STATE_FILE.exists() else None,
        "vault_configured": bool(get_vault_path()),
    }
