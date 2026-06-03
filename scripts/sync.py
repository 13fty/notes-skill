#!/usr/bin/env python3
"""
obsidian_sync.py
================
Parse Claude's obsidian-skill output blocks and write them to a local vault.

Usage:
    python sync.py --vault ~/Documents/MyVault --input output.md
    echo "..." | python sync.py --vault ~/Documents/MyVault

Output block format expected in input:
    ```obsidian-file
    path: Daily/2025-06-03.md
    action: append | create | replace-section
    section: ## AI Sessions          # only required for replace-section / append
    ---
    {file content}
    ```
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# ── Parsing ────────────────────────────────────────────────────────────────────

BLOCK_RE = re.compile(
    r"```obsidian-file\n(.*?)```",
    re.DOTALL,
)

FRONTMATTER_RE = re.compile(r"^(.*?)\n---\n(.*)", re.DOTALL)


def parse_blocks(text: str) -> list[dict]:
    """Extract all obsidian-file blocks from a string."""
    blocks = []
    for match in BLOCK_RE.finditer(text):
        raw = match.group(1)
        fm_match = FRONTMATTER_RE.match(raw)
        if not fm_match:
            print(f"[warn] Skipping malformed block (no --- separator):\n{raw[:80]}")
            continue

        header_text, content = fm_match.groups()
        meta = {}
        for line in header_text.strip().splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                meta[k.strip()] = v.strip()

        if "path" not in meta or "action" not in meta:
            print(f"[warn] Block missing path/action: {meta}")
            continue

        blocks.append(
            {
                "path": meta["path"],
                "action": meta["action"],
                "section": meta.get("section", ""),
                "content": content.strip(),
            }
        )
    return blocks


# ── Writing ────────────────────────────────────────────────────────────────────

def ensure_parent(file_path: Path):
    file_path.parent.mkdir(parents=True, exist_ok=True)


def action_create(file_path: Path, content: str):
    if file_path.exists():
        print(f"[skip] {file_path} already exists (use replace-section to update)")
        return
    ensure_parent(file_path)
    file_path.write_text(content + "\n", encoding="utf-8")
    print(f"[create] {file_path}")


def action_append(file_path: Path, content: str, section: str):
    ensure_parent(file_path)
    if not file_path.exists():
        # Create with content
        file_path.write_text(content + "\n", encoding="utf-8")
        print(f"[create+append] {file_path}")
        return

    existing = file_path.read_text(encoding="utf-8")

    if section:
        # Find section header and append after it (before next same-level header)
        header_level = len(section) - len(section.lstrip("#"))
        pattern = re.compile(
            r"(" + re.escape(section) + r"\n)(.*?)(\n#{1," + str(header_level) + r"} |\Z)",
            re.DOTALL,
        )
        match = pattern.search(existing)
        if match:
            insertion_point = match.start(3)
            new_text = existing[:insertion_point] + "\n" + content + "\n" + existing[insertion_point:]
            file_path.write_text(new_text, encoding="utf-8")
            print(f"[append→{section}] {file_path}")
            return

        # Section doesn't exist — append section + content at end
        new_text = existing.rstrip() + "\n\n" + section + "\n\n" + content + "\n"
        file_path.write_text(new_text, encoding="utf-8")
        print(f"[append+create-section] {file_path}")
    else:
        # No section specified — append at end
        new_text = existing.rstrip() + "\n\n" + content + "\n"
        file_path.write_text(new_text, encoding="utf-8")
        print(f"[append-end] {file_path}")


def action_replace_section(file_path: Path, content: str, section: str):
    if not section:
        print(f"[error] replace-section requires a section header for {file_path}")
        return

    ensure_parent(file_path)
    if not file_path.exists():
        action_create(file_path, section + "\n\n" + content)
        return

    existing = file_path.read_text(encoding="utf-8")
    header_level = len(section) - len(section.lstrip("#"))
    pattern = re.compile(
        r"(" + re.escape(section) + r"\n)(.*?)(\n#{1," + str(header_level) + r"} |\Z)",
        re.DOTALL,
    )
    match = pattern.search(existing)
    if match:
        new_text = (
            existing[: match.start(2)]
            + content
            + "\n"
            + existing[match.start(3):]
        )
        file_path.write_text(new_text, encoding="utf-8")
        print(f"[replace→{section}] {file_path}")
    else:
        # Section missing — append
        action_append(file_path, content, section)


# ── Main ───────────────────────────────────────────────────────────────────────

def apply_block(vault: Path, block: dict):
    file_path = vault / block["path"]
    action = block["action"]
    content = block["content"]
    section = block["section"]

    if action == "create":
        action_create(file_path, content)
    elif action == "append":
        action_append(file_path, content, section)
    elif action == "replace-section":
        action_replace_section(file_path, content, section)
    else:
        print(f"[warn] Unknown action '{action}' for {file_path}")


def main():
    parser = argparse.ArgumentParser(description="Sync Claude obsidian-skill output to vault")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")
    parser.add_argument("--input", help="Input file (default: stdin)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"[error] Vault not found: {vault}")
        sys.exit(1)

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    blocks = parse_blocks(text)
    if not blocks:
        print("[warn] No obsidian-file blocks found in input.")
        sys.exit(0)

    print(f"[info] Found {len(blocks)} block(s). Vault: {vault}")

    for block in blocks:
        if args.dry_run:
            print(f"[dry-run] {block['action']} → {vault / block['path']}  section={block['section'] or 'N/A'}")
        else:
            apply_block(vault, block)

    print(f"[done] {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()