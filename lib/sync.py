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
    """Create a new file. Skips if already exists. Returns status string."""
    if file_path.exists():
        return "skipped"
    _ensure_parent(file_path)
    file_path.write_text(content + "\n", encoding="utf-8")
    return "created"


def _action_append(file_path: Path, content: str, section: str) -> str:
    """Append content to a file, optionally under a specific section. Returns status string."""
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
    """Replace a named section in a file. Creates the file + section if missing. Returns status string."""
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
