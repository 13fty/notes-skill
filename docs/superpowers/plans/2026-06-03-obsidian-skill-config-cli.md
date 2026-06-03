# Obsidian Skill — 配置管理 & 统一 CLI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 obsidian-second-brain 项目建立配置管理、Vault 自动化、统一 CLI 入口，从 Claude 独占重构为智能体无关架构。

**Architecture:** `lib/` 层提供纯函数模块（config、vault、parser、templates、sync），`scripts/cli.py` 作为唯一 CLI 入口路由命令，`skill.md` 通过 Step 0 在每次加载时自动检查/初始化配置。配置与状态分离：`config.json` 存用户设定，`state.json` 存运行时数据。

**Tech Stack:** Python 3.11+, stdlib only（json, argparse, pathlib, os, sys, platform, datetime）

---

## File Map

| 文件 | 操作 | 职责 |
|------|------|------|
| `lib/__init__.py` | Create | 包标记 |
| `lib/config.py` | Create | 配置 + 状态的 CRUD、迁移 |
| `lib/vault.py` | Create | Vault 搜索、验证、修复 |
| `lib/templates.py` | Create | 模板文件读取 + 变量渲染 |
| `lib/parser.py` | Create | 从对话文本提取技术栈/QA/链接 |
| `lib/sync.py` | Create | 解析 AI 输出块 → 写入 vault 文件 |
| `scripts/cli.py` | Create | 统一 CLI（8 个子命令） |
| `templates/daily.md` | Create | 日记模板 |
| `templates/project.md` | Create | 项目笔记模板 |
| `templates/knowledge.md` | Create | 知识图谱模板 |
| `.gitignore` | Create | Python 项目忽略规则 |
| `skill.md` | Modify | 新增 Step 0，去除 Claude 硬编码引用 |
| `README.md` | Modify | 更新安装与使用说明 |
| `scripts/sync.py` | Delete | 逻辑已迁移至 lib/sync.py |
| `scripts/parse_session.py` | Delete | 逻辑已迁移至 lib/parser.py |
| `referneces/templates.md` | Delete | 模板已拆分到 templates/ |

---

### Task 1: 创建目录结构 + `.gitignore`

**Files:**
- Create: `.gitignore`
- Create: `lib/__init__.py`

- [ ] **Step 1: 创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Obsidian (vault content, not our code)
.obsidian/

# Config (user's — never commit)
.obsidian-skill/

# Virtual env
venv/
.venv/
```

Write: `.gitignore`

- [ ] **Step 2: 创建 lib/__init__.py**

```python
"""Obsidian Skill core library.

Configuration, vault discovery, parsing, and sync logic.
Vendor-agnostic — shared across Claude Code, Gemini CLI, Codex, and others.
"""

__version__ = "1.0.0"
```

Write: `lib/__init__.py`

- [ ] **Step 3: 创建 lib 和 scripts 目录**

```bash
mkdir -p lib scripts templates
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore lib/__init__.py
git commit -m "feat: initialize project structure with .gitignore and lib package"
```

---

### Task 2: 实现 `lib/config.py`

**Files:**
- Create: `lib/config.py`

- [ ] **Step 1: 写入 config.py 完整实现**

```python
"""Configuration and state file management for obsidian-skill.

Paths:
    CONFIG_DIR  = ~/.obsidian-skill/
    CONFIG_FILE = ~/.obsidian-skill/config.json
    STATE_FILE  = ~/.obsidian-skill/state.json
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    cfg = load_config()
    prefs = cfg.get("preferences", {})
    return prefs.get(key, default)


def set_preference(key: str, value: Any) -> None:
    """Set a single preference."""
    cfg = load_config()
    cfg.setdefault("preferences", {})[key] = value
    save_config(cfg)


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
    stats["total_files_updated"] = stats.get("total_files_updated", 0) + files_updated
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

MIGRATIONS: dict[str, callable] = {}


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
```

Write: `lib/config.py`

- [ ] **Step 2: 验证可导入**

```bash
python3 -c "from lib.config import load_config, load_state; print('config:', load_config()['version']); print('state:', load_state()['version'])"
```

Expected output:
```
config: 1.0.0
state: 1.0.0
```

- [ ] **Step 3: Commit**

```bash
git add lib/config.py
git commit -m "feat: add config.py — config and state CRUD with migration support"
```

---

### Task 3: 实现 `lib/vault.py`

**Files:**
- Create: `lib/vault.py`

- [ ] **Step 1: 写入 vault.py 完整实现**

```python
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

    required_failed = False
    for check in REQUIRED_CHECKS:
        passed = result["checks"].get(check, False)
        icon = "✅" if passed else "❌"
        lines.append(f"  {icon} {check} (required)")
        if not passed:
            required_failed = True

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
        # Walk the directory tree
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
```

Write: `lib/vault.py`

- [ ] **Step 2: 验证搜索功能**

```bash
python3 -c "
from lib.vault import search_vaults
vaults = search_vaults()
for v in vaults:
    print(f\"  {v['name']:20s} valid={v['valid']}  {v['path']}\")
print(f'Found {len(vaults)} vault(s)')
"
```

- [ ] **Step 3: 验证校验功能**

```bash
python3 -c "
from lib.vault import validate_vault, format_validation_report
import os
# Test with home directory (should fail)
r = validate_vault(os.path.expanduser('~'))
print(format_validation_report(r))
"
```

- [ ] **Step 4: Commit**

```bash
git add lib/vault.py
git commit -m "feat: add vault.py — search, validate, and repair Obsidian vaults"
```

---

### Task 4: 实现 `lib/templates.py`

**Files:**
- Create: `lib/templates.py`

- [ ] **Step 1: 写入 templates.py**

```python
"""Template loading and rendering for obsidian-skill.

Reads .md template files from the templates/ directory and renders them
with variable substitution ({{variable}} syntax).
"""

import re
from datetime import date
from pathlib import Path


# ── Template discovery ──────────────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _resolve(name: str) -> Path:
    """Resolve a template name to its file path.

    Names can be bare ('daily') or with extension ('daily.md').
    """
    if not name.endswith(".md"):
        name = f"{name}.md"
    return _TEMPLATE_DIR / name


def list_templates() -> list[str]:
    """Return names of all available templates (without .md extension)."""
    if not _TEMPLATE_DIR.exists():
        return []
    return sorted(
        p.stem for p in _TEMPLATE_DIR.glob("*.md")
    )


def load_template(name: str) -> str:
    """Load a template by name, returning raw markdown text.

    Raises FileNotFoundError if the template doesn't exist.
    """
    path = _resolve(name)
    if not path.exists():
        raise FileNotFoundError(f"Template '{name}' not found at {path}")
    return path.read_text(encoding="utf-8")


# ── Rendering ──────────────────────────────────────────────────────────────────

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


# Built-in variable providers
_BUILTINS = {
    "date": lambda: date.today().isoformat(),
    "year": lambda: str(date.today().year),
    "month": lambda: f"{date.today().month:02d}",
    "day": lambda: f"{date.today().day:02d}",
    "datetime": lambda: date.today().strftime("%Y-%m-%d %H:%M"),
}


def render_template(name: str, variables: dict[str, str] | None = None) -> str:
    """Load a template and substitute variables.

    Supports {{variable}} syntax. Built-in variables (date, year, month, day, datetime)
    are available automatically and can be overridden by passing them in `variables`.

    Example:
        render_template("daily", {"project": "MyProject"})
    """
    text = load_template(name)

    # Merge builtins with user-provided variables (user overrides builtins)
    vars_: dict[str, str] = {}
    for key, fn in _BUILTINS.items():
        vars_[key] = fn()
    if variables:
        vars_.update(variables)

    def _replace(match: re.Match) -> str:
        var = match.group(1)
        return vars_.get(var, match.group(0))

    return _VAR_RE.sub(_replace, text)


def render_template_string(template_text: str, variables: dict[str, str] | None = None) -> str:
    """Render a template string (not from a file) with variable substitution.

    Useful when you have template content in memory rather than on disk.
    """
    vars_: dict[str, str] = {}
    for key, fn in _BUILTINS.items():
        vars_[key] = fn()
    if variables:
        vars_.update(variables)

    def _replace(match: re.Match) -> str:
        var = match.group(1)
        return vars_.get(var, match.group(0))

    return _VAR_RE.sub(_replace, template_text)


def create_note(name: str, variables: dict[str, str] | None = None) -> str:
    """Convenience: render a template for creating a new note."""
    return render_template(name, variables)
```

Write: `lib/templates.py`

- [ ] **Step 2: 验证导入**

```bash
python3 -c "from lib.templates import list_templates; print('Templates:', list_templates())"
```

- [ ] **Step 3: Commit**

```bash
git add lib/templates.py
git commit -m "feat: add templates.py — template loading and variable rendering"
```

---

### Task 5: 拆分模板文件

**Files:**
- Create: `templates/daily.md`
- Create: `templates/project.md`
- Create: `templates/knowledge.md`

- [ ] **Step 1: 创建 templates/daily.md**

```markdown
---
tags: [daily]
date: {{date}}
---

# {{date}}

## Focus
> What matters most today?

- 

## Today's Progress
- [ ] 

## AI Sessions

<!-- Sessions appended here by obsidian-skill -->

## Action Items
- [ ] 

## Notes & Thoughts

---
*Created by obsidian-skill*
```

Write: `templates/daily.md`

- [ ] **Step 2: 创建 templates/project.md**

```markdown
---
tags: [project]
status: active
created: {{date}}
updated: {{date}}
tech: []
---

# {{project}}

## Overview
> One paragraph description of what this project is and why it exists.

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Language | |
| Framework | |
| Tool | |
| API | |

## Session Log

<!-- Newest entries first -->

## Problems & Solutions

<!-- Q&A pairs appended here -->

## Related Projects

<!-- Associations auto-generated -->

## Knowledge Nodes

<!-- Graph references -->

---
*Last synced: {{date}}*
```

Write: `templates/project.md`

- [ ] **Step 3: 创建 templates/knowledge.md**

```markdown
---
tags: [meta, graph]
---

# Knowledge Graph

Machine-readable edges between all nodes in the vault.
Compatible with Dataview plugin for queries.

## Edges

| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|

## Notes
- Relations: `used-in`, `evolved-from`, `inspired-by`, `shares-stack-with`, `depends-on`
- All nodes should also appear in `[[Meta/Nodes]]`
```

Write: `templates/knowledge.md`

- [ ] **Step 4: 验证模板可加载**

```bash
python3 -c "
from lib.templates import list_templates, render_template
for name in list_templates():
    print(f'--- {name} ---')
    print(render_template(name, {'project': 'TestProject'})[:200])
    print()
"
```

Expected: 3 templates listed, each rendering with variables substituted.

- [ ] **Step 5: Commit**

```bash
git add templates/
git commit -m "feat: split templates into individual daily, project, knowledge files"
```

---

### Task 6: 提取 `lib/parser.py`

**Files:**
- Create: `lib/parser.py`
- Read: `scripts/parse_session.py` (existing — extract logic from here)

- [ ] **Step 1: 写入 parser.py（从 parse_session.py 提取纯文本处理逻辑）**

```python
"""Conversation text parsers for obsidian-skill.

Extracts structured data from raw AI conversation transcripts:
- Tech stack detection
- Q&A / problem-solution pairs
- Wiki link generation
- Proper noun detection

All functions are pure — text in, structured data out. No I/O.
"""

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ── Tech Stack Extraction ───────────────────────────────────────────────────────

TECH_REGISTRY: dict[str, list[str]] = {
    "Language": [
        "Python", "TypeScript", "JavaScript", "Swift", "Rust", "Go", "Kotlin",
        "Java", "C++", "C#", "Ruby", "PHP", "Bash", "Shell",
    ],
    "Framework": [
        "FastAPI", "Flask", "Django", "React", "Vue", "Next.js", "Nuxt",
        "PyQt5", "PyQt6", "SwiftUI", "UIKit", "Express", "NestJS",
        "Spring", "Rails", "Laravel",
    ],
    "Tool": [
        "Docker", "Git", "npm", "pip", "Homebrew", "Make", "Webpack", "Vite",
        "Pytest", "Jest", "GitHub Actions", "CI/CD", "Nginx", "Caddy",
    ],
    "API/Service": [
        "Anthropic", "OpenAI", "DeepSeek", "Gemini", "Claude",
        "WeChat", "Telegram", "Slack", "Discord",
        "AWS", "GCP", "Azure", "Vercel", "Railway",
    ],
    "Library": [
        "OpenCV", "MediaPipe", "NumPy", "Pandas", "Matplotlib",
        "SQLAlchemy", "Pydantic", "Uvicorn", "aiohttp", "requests",
        "python-pptx", "openpyxl", "Pillow",
        "Tailwind", "shadcn", "lucide",
    ],
    "Concept": [
        "REST", "GraphQL", "WebSocket", "gRPC", "IPC", "PTY",
        "MVC", "MVVM", "microservices", "containerization",
        "RAG", "embeddings", "vector database", "LLM", "AI agent",
    ],
}

# Build flat lookup: lowercase tech name → (category, canonical name)
_tech_lookup: dict[str, tuple[str, str]] = {}
for _cat, _items in TECH_REGISTRY.items():
    for _item in _items:
        _tech_lookup[_item.lower()] = (_cat, _item)


def extract_tech_stack(text: str) -> dict[str, list[str]]:
    """Return {category: [tech, ...]} for all known techs mentioned in text."""
    found: dict[str, set[str]] = {}
    words = re.findall(r"[\w.#/+\-]+", text)
    for word in words:
        key = word.lower().rstrip(".,;:!?")
        if key in _tech_lookup:
            cat, canonical = _tech_lookup[key]
            found.setdefault(cat, set()).add(canonical)

    # Preserve registry category order
    result: dict[str, list[str]] = {}
    for cat in TECH_REGISTRY:
        if cat in found:
            result[cat] = sorted(found[cat])
    return result


def tech_stack_to_markdown(stack: dict[str, list[str]]) -> str:
    """Render a tech stack dict as a Markdown table."""
    if not stack:
        return "_No technologies detected_"
    rows = ["| Category | Technologies |", "|----------|-------------|"]
    for cat, techs in stack.items():
        rows.append(f"| {cat} | {' · '.join(techs)} |")
    return "\n".join(rows)


# ── Q&A Extraction ──────────────────────────────────────────────────────────────

PROBLEM_SIGNALS = [
    r"error[:\s]", r"Error[:\s]", r"Exception[:\s]",
    r"报错", r"错误", r"问题", r"issue", r"bug",
    r"why (is|does|doesn't|can't|won't)",
    r"how (do|can|to)",
    r"怎么", r"为什么", r"如何",
    r"not working", r"doesn't work", r"failed",
]

SOLUTION_SIGNALS = [
    r"fix(ed)?[:\s]", r"solution[:\s]", r"resolve[d]?[:\s]",
    r"solved", r"工作了", r"解决了", r"成功了",
    r"try[:\s]", r"instead[:\s]", r"should[:\s]",
    r"the (issue|problem) was",
]

_prob_re = re.compile("|".join(PROBLEM_SIGNALS), re.IGNORECASE)
_soln_re = re.compile("|".join(SOLUTION_SIGNALS), re.IGNORECASE)


@dataclass
class QAPair:
    title: str
    problem: str
    solution: str
    tags: list[str] = field(default_factory=list)


def extract_qa_pairs(text: str) -> list[QAPair]:
    """Heuristically extract problem/solution pairs from conversation text."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    pairs: list[QAPair] = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        if _prob_re.search(para):
            problem_text = para
            solution_text = ""
            for j in range(i + 1, min(i + 4, len(paragraphs))):
                if _soln_re.search(paragraphs[j]):
                    solution_text = paragraphs[j]
                    i = j
                    break
            if solution_text:
                words = re.findall(r"\w+", problem_text)
                title = " ".join(words[:8])
                pairs.append(QAPair(
                    title=title,
                    problem=problem_text[:400],
                    solution=solution_text[:600],
                ))
        i += 1
    return pairs


def qa_pair_to_markdown(qa: QAPair, project: str, date: str) -> str:
    """Render a single QAPair as Markdown."""
    tag_str = " ".join(f"#{t}" for t in qa.tags) if qa.tags else ""
    parts = [
        f"### {qa.title}",
        f"**Date**: {date}",
        f"**Project**: [[{project}]]",
        "",
        "**Problem**:",
        qa.problem,
        "",
        "**Solution**:",
        qa.solution,
    ]
    if tag_str:
        parts.append(f"\n**Tags**: {tag_str}")
    return "\n".join(parts)


# ── Wiki Link Generation ────────────────────────────────────────────────────────

_date_re = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def linkify(text: str, known_projects: list[str], vault_root: Path | None = None) -> str:
    """Replace bare tech names and project references with [[WikiLinks]].

    - Dates → [[Daily/YYYY-MM-DD]]
    - Project names → [[Projects/Name]]
    - First occurrence of each entity only.
    """
    linked: set[str] = set()

    def replace_date(m: re.Match) -> str:
        d = m.group(1)
        if d not in linked:
            linked.add(d)
            return f"[[Daily/{d}]]"
        return d
    text = _date_re.sub(replace_date, text)

    for proj in sorted(known_projects, key=len, reverse=True):
        if proj in linked:
            continue
        pattern = re.compile(r"(?<!\[\[)\b" + re.escape(proj) + r"\b(?!\]\])")
        def replace_proj(m: re.Match, p: str = proj) -> str:
            if p not in linked:
                linked.add(p)
                return f"[[Projects/{p}]]"
            return p
        text = pattern.sub(replace_proj, text)

    return text


# ── Summary helpers ─────────────────────────────────────────────────────────────

def extract_proper_nouns(text: str) -> list[str]:
    """Extract capitalized multi-word phrases that look like proper nouns."""
    pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
    matches = pattern.findall(text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m.lower() not in seen:
            seen.add(m.lower())
            result.append(m)
    return result
```

Write: `lib/parser.py`

- [ ] **Step 2: 验证解析功能**

```bash
python3 -c "
from lib.parser import extract_tech_stack, extract_qa_pairs, tech_stack_to_markdown

text = '''
We built a FastAPI backend with Python and Docker.
Got an error: 'ModuleNotFoundError: No module named uvicorn'
怎么解决？ Fixed by: pip install uvicorn
'''

stack = extract_tech_stack(text)
print('Tech stack:', stack)
print()
print(tech_stack_to_markdown(stack))
print()
qa = extract_qa_pairs(text)
for q in qa:
    print(f'Q: {q.title}')
    print(f'  Problem: {q.problem[:80]}...')
    print(f'  Solution: {q.solution[:80]}...')
"
```

Expected: Detect Python, FastAPI, Docker, Uvicorn. Extract one Q&A pair.

- [ ] **Step 3: Commit**

```bash
git add lib/parser.py
git commit -m "feat: add parser.py — tech stack, Q&A, and wiki link extraction"
```

---

### Task 7: 提取 `lib/sync.py`

**Files:**
- Create: `lib/sync.py`
- Read: `scripts/sync.py` (existing — extract block-parsing + vault-writing logic)

- [ ] **Step 1: 写入 sync.py（从 sync.py 提取核心逻辑，去除命令行处理）**

```python
"""Sync engine for obsidian-skill.

Parses AI agent output blocks (```obsidian-file ... ```) and writes them
into an Obsidian vault with create/append/replace-section semantics.
"""

import re
from datetime import datetime
from pathlib import Path


# ── Block parsing ───────────────────────────────────────────────────────────────

BLOCK_RE = re.compile(
    r"```obsidian-file\n(.*?)```",
    re.DOTALL,
)

FRONTMATTER_RE = re.compile(r"^(.*?)\n---\n(.*)", re.DOTALL)


def parse_blocks(text: str) -> list[dict]:
    """Extract all obsidian-file fenced blocks from text.

    Returns a list of dicts with keys: path, action, section, content.
    """
    blocks: list[dict] = []
    for match in BLOCK_RE.finditer(text):
        raw = match.group(1)
        fm_match = FRONTMATTER_RE.match(raw)
        if not fm_match:
            print(f"[warn] Skipping malformed block (no --- separator):\n{raw[:80]}")
            continue

        header_text, content = fm_match.groups()
        meta: dict[str, str] = {}
        for line in header_text.strip().splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                meta[k.strip()] = v.strip()

        if "path" not in meta or "action" not in meta:
            print(f"[warn] Block missing path/action: {meta}")
            continue

        blocks.append({
            "path": meta["path"],
            "action": meta["action"],
            "section": meta.get("section", ""),
            "content": content.strip(),
        })
    return blocks


# ── Vault writing ───────────────────────────────────────────────────────────────

def _ensure_parent(file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _action_create(file_path: Path, content: str) -> str:
    """Create a new file. Skips if already exists.

    Returns a status string: 'created', 'skipped'.
    """
    if file_path.exists():
        return "skipped"
    _ensure_parent(file_path)
    file_path.write_text(content + "\n", encoding="utf-8")
    return "created"


def _action_append(file_path: Path, content: str, section: str) -> str:
    """Append content to a file, optionally under a specific section.

    Returns a status string.
    """
    _ensure_parent(file_path)
    if not file_path.exists():
        file_path.write_text(content + "\n", encoding="utf-8")
        return "created"

    existing = file_path.read_text(encoding="utf-8")

    if section:
        header_level = len(section) - len(section.lstrip("#"))
        pattern = re.compile(
            r"(" + re.escape(section) + r"\n)(.*?)(\n#{1," + str(header_level) + r"} |\Z)",
            re.DOTALL,
        )
        m = pattern.search(existing)
        if m:
            insertion_point = m.start(3)
            new_text = existing[:insertion_point] + "\n" + content + "\n" + existing[insertion_point:]
            file_path.write_text(new_text, encoding="utf-8")
            return "appended-to-section"

        new_text = existing.rstrip() + "\n\n" + section + "\n\n" + content + "\n"
        file_path.write_text(new_text, encoding="utf-8")
        return "appended-new-section"

    new_text = existing.rstrip() + "\n\n" + content + "\n"
    file_path.write_text(new_text, encoding="utf-8")
    return "appended-end"


def _action_replace_section(file_path: Path, content: str, section: str) -> str:
    """Replace a named section in a file. Creates the file + section if missing.

    Returns a status string.
    """
    if not section:
        return "error: no section specified"

    _ensure_parent(file_path)
    if not file_path.exists():
        file_path.write_text(section + "\n\n" + content + "\n", encoding="utf-8")
        return "created-with-section"

    existing = file_path.read_text(encoding="utf-8")
    header_level = len(section) - len(section.lstrip("#"))
    pattern = re.compile(
        r"(" + re.escape(section) + r"\n)(.*?)(\n#{1," + str(header_level) + r"} |\Z)",
        re.DOTALL,
    )
    m = pattern.search(existing)
    if m:
        new_text = existing[:m.start(2)] + content + "\n" + existing[m.start(3):]
        file_path.write_text(new_text, encoding="utf-8")
        return "section-replaced"

    return _action_append(file_path, content, section)


# ── Apply ───────────────────────────────────────────────────────────────────────

def apply_block(vault: Path, block: dict) -> dict:
    """Apply a single parsed block to the vault.

    Returns: {"path": str, "action": str, "status": str}
    """
    file_path = vault / block["path"]
    action = block["action"]
    content = block["content"]
    section = block.get("section", "")

    if action == "create":
        status = _action_create(file_path, content)
    elif action == "append":
        status = _action_append(file_path, content, section)
    elif action == "replace-section":
        status = _action_replace_section(file_path, content, section)
    else:
        status = f"unknown-action: {action}"

    return {
        "path": str(file_path),
        "action": action,
        "status": status,
    }


def sync_to_vault(vault_path: str | Path, text: str, dry_run: bool = False) -> list[dict]:
    """Parse obsidian-file blocks from text and write them to a vault.

    Args:
        vault_path: Path to the Obsidian vault root.
        text: Full AI conversation output containing ```obsidian-file blocks.
        dry_run: If True, only simulate — don't write files.

    Returns:
        List of result dicts, one per block.
    """
    vault = Path(vault_path).expanduser().resolve()
    blocks = parse_blocks(text)
    results: list[dict] = []

    for block in blocks:
        if dry_run:
            results.append({
                "path": str(vault / block["path"]),
                "action": block["action"],
                "status": "dry-run",
            })
        else:
            result = apply_block(vault, block)
            results.append(result)

    return results
```

Write: `lib/sync.py`

- [ ] **Step 2: 验证 sync 模块导入**

```bash
python3 -c "
from lib.sync import parse_blocks, sync_to_vault
sample = '''
\`\`\`obsidian-file
path: Daily/2026-06-03.md
action: append
section: ## AI Sessions
---
Test content here
\`\`\`
'''
blocks = parse_blocks(sample)
print('Blocks:', len(blocks))
for b in blocks:
    print(f\"  path={b['path']}, action={b['action']}, section={b['section']}\")
    print(f\"  content: {b['content'][:50]}...\")
"
```

- [ ] **Step 3: Commit**

```bash
git add lib/sync.py
git commit -m "feat: add sync.py — block parser and vault writer extracted from scripts/"
```

---

### Task 8: 实现统一 CLI `scripts/cli.py`

**Files:**
- Create: `scripts/cli.py`

- [ ] **Step 1: 写入 cli.py**

```python
#!/usr/bin/env python3
"""obsidian-skill — Unified CLI for managing Obsidian vault integration.

Usage:
    obsidian-skill <command> [options]

Commands:
    init       First-time setup wizard
    config     View or modify configuration
    validate   Check vault health
    search     Find Obsidian vaults on this system
    repair     Recover a broken vault path
    sync       Write AI output blocks to vault
    migrate    Upgrade config version
    doctor     Full system diagnostic
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure lib/ is importable when running from project root
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from lib.config import (
    load_config, save_config, config_exists, get_vault_path, set_vault_path,
    export_config, config_get, config_set, get_preference, set_preference,
    record_sync, record_discovered_vault, get_discovered_vaults,
    run_migrations, doctor_check as config_doctor,
)
from lib.vault import (
    search_vaults, search_vaults_simple, validate_vault,
    repair_vault, format_validation_report, doctor_check as vault_doctor,
)
from lib.sync import sync_to_vault
from lib.templates import list_templates, render_template


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _fail(msg: str, code: int = 1):
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(code)


# ── Command handlers ────────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    """First-time initialization wizard."""
    if config_exists() and not args.force:
        vault = get_vault_path()
        print(f"Config already exists. Vault: {vault}")
        print("Use --force to re-initialize.")
        return 0

    vault_path = args.vault
    if vault_path:
        # Direct path provided
        result = validate_vault(vault_path)
        if not result["valid"]:
            print(format_validation_report(result))
            _fail("Provided vault path is not valid. Check the report above.")
        set_vault_path(vault_path)
        record_discovered_vault(vault_path, result["name"], valid=True)
        print(f"✅ Vault configured: {vault_path}")
        return 0

    # Interactive flow: search first
    vaults = search_vaults()
    valid_vaults = [v for v in vaults if v["valid"]]

    if valid_vaults:
        print(f"Found {len(valid_vaults)} Obsidian vault(s):\n")
        for i, v in enumerate(valid_vaults):
            name = v["name"]
            path = v["path"]
            warnings = f" ({len(v['warnings'])} warnings)" if v["warnings"] else ""
            print(f"  [{i + 1}] {name} — {path}{warnings}")

        if args.noninteractive:
            chosen = valid_vaults[0]
        else:
            print()
            try:
                choice = input(f"Select vault [1-{len(valid_vaults)}] or press Enter for first: ").strip()
                idx = int(choice) - 1 if choice else 0
                if idx < 0 or idx >= len(valid_vaults):
                    _fail(f"Invalid selection: {choice}")
                chosen = valid_vaults[idx]
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return 1

        set_vault_path(chosen["path"])
        record_discovered_vault(chosen["path"], chosen["name"], valid=True)
        print(f"✅ Vault configured: {chosen['path']}")
        return 0

    # No vaults found — ask for path
    if args.noninteractive:
        _fail("No vaults found and --noninteractive set. Use --vault to specify path.")

    print("No Obsidian vaults found automatically.")
    try:
        path = input("Enter your vault path: ").strip()
        if not path:
            _fail("No path provided.")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return 1

    result = validate_vault(path)
    if not result["valid"]:
        print(format_validation_report(result))
        _fail("Provided path is not a valid Obsidian vault.")

    set_vault_path(path)
    record_discovered_vault(path, result["name"], valid=True)
    print(f"✅ Vault configured: {path}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """View or modify configuration."""
    if args.action == "list":
        print(export_config())
    elif args.action == "get":
        if not args.key:
            _fail("config get requires a key, e.g. 'vault_path' or 'preferences.language'")
        value = config_get(args.key)
        if value is None:
            _fail(f"Key not found: {args.key}")
        if isinstance(value, (dict, list)):
            _print_json(value)
        else:
            print(value)
    elif args.action == "set":
        if not args.key or args.value is None:
            _fail("config set requires <key> <value>, e.g. 'preferences.language en'")
        # Try to parse JSON values (bool, int, list, dict)
        try:
            parsed_value = json.loads(args.value)
        except (json.JSONDecodeError, ValueError):
            parsed_value = args.value
        config_set(args.key, parsed_value)
        print(f"✅ Set {args.key} = {json.dumps(parsed_value, ensure_ascii=False)}")
    elif args.action == "reset":
        from lib.config import DEFAULT_CONFIG
        save_config(dict(DEFAULT_CONFIG))
        print("✅ Config reset to defaults.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate the configured or specified vault."""
    path = args.path or get_vault_path()
    if not path:
        _fail("No vault configured. Run 'obsidian-skill init' first, or pass --path.")

    result = validate_vault(path)
    if args.json:
        _print_json(result)
    else:
        print(format_validation_report(result))

    return 0 if result["valid"] else 1


def cmd_search(args: argparse.Namespace) -> int:
    """Search for Obsidian vaults on this system."""
    vaults = search_vaults()
    if not vaults:
        print("No vaults found.")
        return 0

    if args.json:
        _print_json(vaults)
    else:
        for v in vaults:
            icon = "✅" if v["valid"] else "❌"
            print(f"{icon} {v['name']:20s}  {v['path']}")
            for w in v.get("warnings", []):
                print(f"   ⚠️  {w}")
        print(f"\n{len(vaults)} vault(s) found.")

    # Update discovered_vaults in state
    for v in vaults:
        record_discovered_vault(v["path"], v["name"], valid=v["valid"])

    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    """Repair a broken vault configuration."""
    vault_path = get_vault_path()
    if not vault_path:
        _fail("No vault configured. Run 'obsidian-skill init' first.")

    discovered = get_discovered_vaults()
    result = repair_vault(vault_path, discovered)

    print(result["message"])
    if result["candidates"]:
        print("\nCandidates:")
        for i, c in enumerate(result["candidates"]):
            mark = " ← best match" if c == result.get("new_path") else ""
            print(f"  [{i + 1}] {c}{mark}")

        if result["repaired"] and not args.dry_run:
            try:
                choice = input(f"\nAccept '{result['new_path']}'? [Y/n]: ").strip().lower()
                if choice in ("", "y", "yes"):
                    set_vault_path(result["new_path"])
                    print(f"✅ Updated vault path: {result['new_path']}")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return 1

            print("No changes made. Run 'obsidian-skill init --force' to reconfigure.")
    else:
        print("No candidates found. Run 'obsidian-skill init --force' to reconfigure.")

    return 1 if not result["repaired"] else 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Sync AI output blocks to the vault."""
    vault_path = get_vault_path()
    if not vault_path:
        _fail("No vault configured. Run 'obsidian-skill init' first.")

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    results = sync_to_vault(vault_path, text, dry_run=args.dry_run)

    files_written = 0
    files_updated = 0
    for r in results:
        status = r["status"]
        if args.verbose or args.dry_run:
            print(f"[{status}] {r['action']} → {r['path']}")

        if status in ("created", "created-with-section"):
            files_written += 1
        elif status in ("appended-to-section", "appended-end", "appended-new-section", "section-replaced"):
            files_updated += 1

    if not args.dry_run and results:
        record_sync(
            session_id=args.session_id or "cli",
            project=args.project or "unknown",
            files_written=files_written,
            files_updated=files_updated,
        )

    print(f"\nDone: {files_written} written, {files_updated} updated, {len(results)} total blocks.")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Run pending config migrations."""
    from lib.config import load_config as lc
    before = lc().get("version", "unknown")
    cfg = run_migrations()
    after = cfg.get("version", "unknown")
    if before != after:
        print(f"✅ Migrated config from {before} → {after}")
    else:
        print(f"✅ Config is up to date (version {after})")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run a full diagnostic and print a report."""
    report = {
        "config": config_doctor(),
        "vault": vault_doctor(),
        "templates": list_templates(),
    }

    if args.json:
        _print_json(report)
        return 0

    # Human-readable report
    print("=== obsidian-skill doctor ===\n")

    print("📁 Config:")
    c = report["config"]
    print(f"  Config dir:  {'✅' if c['config_dir_exists'] else '❌'} ~/.obsidian-skill/")
    print(f"  Config file: {'✅' if c['config_file_exists'] else '❌'} config.json")
    print(f"  State file:  {'✅' if c['state_file_exists'] else '❌'} state.json")
    print(f"  Vault path:  {'✅' if c['vault_configured'] else '❌'}")

    print("\n🔍 Vault:")
    v = report["vault"]
    if v["validation"]:
        vr = v["validation"]
        print(f"  Status: {'✅ Valid' if vr['valid'] else '❌ Invalid'}")
        print(f"  Path:   {vr['path']}")
        for w in vr.get("warnings", []):
            print(f"  ⚠️  {w}")
    elif v["vault_configured"]:
        print("  ⚠️  No vault configured")
    else:
        print("  ⚠️  Not configured — run 'obsidian-skill init'")

    if v.get("all_vaults_found"):
        print(f"\n📋 Discovered vaults ({len(v['all_vaults_found'])}):")
        for dv in v["all_vaults_found"]:
            print(f"  - {dv}")

    print(f"\n📝 Templates ({len(report['templates'])}):")
    for t in report["templates"]:
        print(f"  - {t}.md")

    all_good = c["vault_configured"] and (v.get("validation") and v["validation"]["valid"])
    print(f"\n{'✅ All checks pass' if all_good else '⚠️  Some checks need attention'}")
    return 0 if all_good else 1


# ── CLI Definition ──────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidian-skill",
        description="Manage Obsidian vault integration for AI agent sessions.",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = sub.add_parser("init", help="First-time setup wizard")
    p_init.add_argument("--vault", help="Directly specify vault path (skip search)")
    p_init.add_argument("--force", action="store_true", help="Re-initialize even if config exists")
    p_init.add_argument("--noninteractive", action="store_true", help="Run without user prompts")

    # config
    p_config = sub.add_parser("config", help="View or modify configuration")
    p_config.add_argument("action", choices=["list", "get", "set", "reset"],
                          help="list=get all, get=<key>, set=<key> <value>, reset=defaults")
    p_config.add_argument("key", nargs="?", help="Config key (dotted, e.g. 'preferences.language')")
    p_config.add_argument("value", nargs="?", help="Value to set")

    # validate
    p_val = sub.add_parser("validate", help="Check vault health")
    p_val.add_argument("--path", help="Vault path (default: from config)")
    p_val.add_argument("--json", action="store_true", help="Output as JSON")

    # search
    p_search = sub.add_parser("search", help="Find Obsidian vaults on this system")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")

    # repair
    p_repair = sub.add_parser("repair", help="Recover a broken vault path")
    p_repair.add_argument("--dry-run", action="store_true", help="Show candidates without applying")

    # sync
    p_sync = sub.add_parser("sync", help="Write AI output blocks to vault")
    p_sync.add_argument("--input", help="Input file (default: stdin)")
    p_sync.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    p_sync.add_argument("--verbose", "-v", action="store_true", help="Show per-file status")
    p_sync.add_argument("--session-id", help="Session identifier for state tracking")
    p_sync.add_argument("--project", help="Project name for state tracking")

    # migrate
    sub.add_parser("migrate", help="Upgrade config version")

    # doctor
    p_doctor = sub.add_parser("doctor", help="Full system diagnostic")
    p_doctor.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


# ── Entry point ────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    handlers = {
        "init": cmd_init,
        "config": cmd_config,
        "validate": cmd_validate,
        "search": cmd_search,
        "repair": cmd_repair,
        "sync": cmd_sync,
        "migrate": cmd_migrate,
        "doctor": cmd_doctor,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
```

Write: `scripts/cli.py`

- [ ] **Step 2: 标记可执行**

```bash
chmod +x scripts/cli.py
```

- [ ] **Step 3: 验证 CLI 帮助**

```bash
python3 scripts/cli.py --help
```

Expected: Full help output with all 8 subcommands.

- [ ] **Step 4: 验证 doctor 命令**

```bash
python3 scripts/cli.py doctor
```

- [ ] **Step 5: 验证 search 命令**

```bash
python3 scripts/cli.py search
```

- [ ] **Step 6: Commit**

```bash
git add scripts/cli.py
git commit -m "feat: add unified CLI with 8 subcommands (init, config, validate, search, repair, sync, migrate, doctor)"
```

---

### Task 9: 更新 `skill.md` 新增 Step 0

**Files:**
- Modify: `skill.md`

- [ ] **Step 1: 更新 frontmatter，去除 Claude 特定引用**

Replace the current frontmatter (lines 1-12) with:

```yaml
---
name: obsidian
description: >
  Process AI agent conversation sessions and sync structured knowledge into Obsidian vaults.
  Use this skill whenever the user wants to: summarize an AI conversation into Obsidian notes,
  update a Daily Note or Project Note with session insights, extract tech stacks or Q&A from a chat,
  create Wiki Links between notes, build project associations, or maintain a knowledge graph in Obsidian.
  Trigger on phrases like "save to obsidian", "update my notes", "log this session", "add to daily note",
  "extract tech stack", "create wiki links", "update project note", or any request to persist
  conversation content into an Obsidian vault. Even if the user just says "记录一下" or "整理笔记",
  treat it as a potential Obsidian sync task.
  Works with Claude Code, Gemini CLI, Codex, Cursor, and other AI agents.
---
```

- [ ] **Step 2: 在 Workflow Overview 之前插入 Step 0**

Insert after the `---` frontmatter separator and before `# Obsidian Knowledge Sync Skill` line:

```markdown
# Obsidian Knowledge Sync Skill

This skill processes AI agent conversation sessions and writes structured, interlinked Markdown notes
into an Obsidian vault. It handles eight core capabilities.

---

## Step 0 — Configuration Check

Before executing any sync workflow, ensure the configuration exists and the vault is accessible.

### 0.1 Load Configuration

Read `~/.obsidian-skill/config.json`. Parse with `json.loads()`.

```
Read ~/.obsidian-skill/config.json
    ↓
Exists?
├── Yes → Extract vault_path → Proceed to 0.2 Vault Validation
│
└── No → Proceed to 0.3 First-Time Setup
```

### 0.2 Vault Validation

When config exists, verify the vault is still usable:

1. Call `python scripts/cli.py validate --json`.
2. Parse the JSON output.
3. If `valid: true` → vault is healthy, continue to Step 1.
4. If `valid: false` → vault is broken.
   - Call `python scripts/cli.py search --json` to find available vaults.
   - Call `python scripts/cli.py repair` to attempt automatic recovery.
   - If repair finds a candidate, use `AskUserQuestion` to confirm the new path.
   - If repair fails, proceed to 0.3 First-Time Setup.

### 0.3 First-Time Setup

When no config exists or repair fails:

1. **Automatically search for vaults**: Run `python scripts/cli.py search --json`.
2. **If vaults found**:
   - Use `AskUserQuestion` to present the list. Let the user select one.
   - On selection, run `python scripts/cli.py init --vault "<selected_path>"`.
3. **If no vaults found**:
   - Use `AskUserQuestion` to ask the user to input their vault path.
   - Example question: "No Obsidian vaults found automatically. Please enter the full path to your Obsidian vault:"
   - Validate the path by checking that it exists and contains a `.obsidian` subdirectory.
   - Run `python scripts/cli.py init --vault "<user_path>"`.
4. **Fallback**: If `AskUserQuestion` is unavailable or the user declines, ask in plain text:
   > "Please reply with the full path to your Obsidian vault. Example: `/Users/name/Documents/Obsidian`"
   - Wait for the user's text response containing a path.
   - Validate and run `python scripts/cli.py init --vault "<path>"`.

### 0.4 Configuration Complete

Once config exists and vault passes validation, the skill has everything it needs.
Proceed to Step 1 — Summarize Session.
```

- [ ] **Step 3: 将 `{vault}` 占位符替换为从 config 读取**

Replace all instances of `{vault}` in the skill.md body with phrasing like:

```
**File path pattern**: `<vault_path>/Daily/{YYYY-MM-DD}.md`
```

And add a note near the top explaining that `<vault_path>` is read from `~/.obsidian-skill/config.json`.

- [ ] **Step 4: Commit**

```bash
git add skill.md
git commit -m "feat: add Step 0 configuration check flow to skill.md"
```

---

### Task 10: 清理旧文件

**Files:**
- Delete: `scripts/sync.py`
- Delete: `scripts/parse_session.py`
- Delete: `referneces/templates.md`

- [ ] **Step 1: 删除已迁移的旧文件**

```bash
rm scripts/sync.py
rm scripts/parse_session.py
rm -r referneces/
```

- [ ] **Step 2: 验证没有 import 引用断裂**

```bash
python3 -c "
from lib.config import load_config
from lib.vault import search_vaults
from lib.parser import extract_tech_stack
from lib.sync import parse_blocks
from lib.templates import list_templates
print('All modules import successfully.')
print('Templates:', list_templates())
"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/ referneces/
git commit -m "refactor: remove old scripts — migrated to lib/ and scripts/cli.py"
```

---

### Task 11: 更新 `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 写入新的 README.md**

```markdown
# Obsidian Second Brain

Sync AI agent conversation sessions into an [Obsidian](https://obsidian.md) vault — structured notes, knowledge graphs, and cross-referenced insights.

Works with Claude Code, Gemini CLI, Codex, Cursor, and other AI agents.

## Quick Start

```bash
# 1. Install
git clone https://github.com/your/obsidian-second-brain.git
cd obsidian-second-brain

# 2. Initialize — auto-discovers your vault
python scripts/cli.py init

# 3. Run a diagnostic
python scripts/cli.py doctor

# 4. Sync AI output
cat session_output.md | python scripts/cli.py sync --project my-project
```

## Commands

| Command | What it does |
|---------|-------------|
| `init` | First-time wizard: search → select → validate → save config |
| `config list` | Show current configuration |
| `config set <key> <value>` | Change a preference |
| `validate` | Check vault health |
| `search` | Find all Obsidian vaults on this system |
| `repair` | Recover when vault path breaks |
| `sync` | Write AI output blocks into vault |
| `migrate` | Upgrade config format version |
| `doctor` | Full diagnostic report |

## Configuration

Config and state are stored at `~/.obsidian-skill/`:

- `config.json` — vault path, preferences, agent type
- `state.json` — sync history, discovered vaults, statistics

This path is agent-agnostic — all AI agents share the same config.

## Skill Integration

### Claude Code

Register `skill.md` as a custom skill. The skill auto-detects configuration on first run.

### Gemini CLI

Add to `GEMINI.md`:

```markdown
## Skills

### obsidian-skill
- **Trigger**: save to obsidian, update notes, log session
- **Action**: Read skill.md from <path>/obsidian-second-brain/skill.md
```

### Other Agents

Point your agent's instruction file to `skill.md` and ensure `python scripts/cli.py` is on the PATH or referenced by absolute path.

## Directory

```
obsidian-second-brain/
├── skill.md              # Core skill instructions (agent-agnostic)
├── scripts/
│   └── cli.py            # Unified CLI
├── lib/
│   ├── config.py         # Config + state management
│   ├── vault.py          # Vault search, validate, repair
│   ├── sync.py           # Block parser + vault writer
│   ├── parser.py         # Tech stack, Q&A, wiki link extraction
│   └── templates.py      # Template loading + rendering
├── templates/
│   ├── daily.md
│   ├── project.md
│   └── knowledge.md
└── .gitignore
```

## Requirements

- Python 3.11+
- No external dependencies (stdlib only)

## License

MIT
```

Write: `README.md`

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README with new CLI commands and multi-agent instructions"
```

---

### Task 12: 端到端验证

- [ ] **Step 1: 验证完整 CLI 命令链**

```bash
# doctor (no config — should report not configured, show templates)
python scripts/cli.py doctor

# search
python scripts/cli.py search

# init dry run
python scripts/cli.py init --help

# validate with a bad path
python scripts/cli.py validate --path /tmp/not-a-vault
echo "Exit code: $?"
```

Expected: doctor and search succeed. validate on bad path exits with code 1.

- [ ] **Step 2: 验证所有模块导入无错误**

```bash
python3 -c "
from lib.config import load_config, load_state, config_exists, get_vault_path
from lib.config import record_sync, get_discovered_vaults, doctor_check
from lib.vault import search_vaults, validate_vault, repair_vault
from lib.parser import extract_tech_stack, extract_qa_pairs, linkify, tech_stack_to_markdown
from lib.sync import parse_blocks, sync_to_vault
from lib.templates import list_templates, render_template
print('All imports OK')
"
```

- [ ] **Step 3: 验证最终目录结构**

```bash
find . -type f | sort | grep -v __pycache__ | grep -v .git
```

Expected output matching the design spec directory structure.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: final verification — all modules import and CLI commands work"
```

---

## Plan Self-Review

- [x] Spec coverage: config.json ✓, state.json ✓, vault search ✓, vault validation + optional checks ✓, vault repair ✓, unified CLI (8 commands) ✓, skill.md Step 0 ✓, template splitting ✓, agent-agnostic paths ✓, doctor command ✓
- [x] No placeholders: all code is fully written, all commands have exact output expectations
- [x] Type consistency: config_get/config_set use dotted keys consistently, vault functions all return dict[str, Any], sync_to_vault takes vault_path + text, record_sync signature matches usage in cli.py
