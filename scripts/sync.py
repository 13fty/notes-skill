#!/usr/bin/env python3
"""Write knowledge output into an Obsidian vault following the 3-layer note framework.

Two input modes:

1. obsidian-file blocks (design standard) — the AI outputs fenced blocks:
   ```obsidian-file
   path: Daily/2026-06-07.md
   action: append | create | replace-section
   section: ## Sessions
   ---
   {content}
   ```

2. JSON pipeline (backward-compatible) — a parse_session.py JSON output:
   python scripts/sync.py --input /tmp/parsed.json

Vault layout (per obsidian-note-framework.md):
  Sessions/   — YYYY-MM-DD-HHMM.md session logs
  Projects/   — {ProjectName}.md project notes with Changelog
  Daily/      — YYYY-MM-DD.md daily notes with Sessions table
  Knowledge/  — {ConceptName}.md unified knowledge nodes
  Meta/       — Knowledge-Graph.md + Projects-Index.md

Usage:
    python scripts/sync.py --vault ~/Documents/MyVault --input output.md
    cat output.md | python scripts/sync.py --vault ~/Documents/MyVault
    python scripts/sync.py --vault ~/Documents/MyVault --input parsed.json
    python scripts/sync.py --vault ~/Documents/MyVault --input output.md --dry-run
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "vault_config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"Config not found: {CONFIG_FILE}", file=sys.stderr)
        print("Run `python scripts/setup.py` first.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def time_now() -> str:
    return datetime.now(timezone.utc).strftime("%H%M")


# ═══════════════════════════════════════════════════════════════════════════════
# obsidian-file block parser
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Block:
    path: str
    action: str
    section: str | None
    content: str


def parse_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    pattern = re.compile(r"```obsidian-file\s*\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(text):
        blocks.append(_parse_single_block(match.group(1)))
    return blocks


def _parse_single_block(body: str) -> Block:
    path = ""
    action = "append"
    section: str | None = None
    content = ""

    sep_idx = body.find("\n---\n")
    if sep_idx >= 0:
        header_text = body[:sep_idx]
        content = body[sep_idx + 5:].strip()
    else:
        header_text = body
        content = ""

    for line in header_text.split("\n"):
        line = line.strip()
        if line.startswith("path:"):
            path = line.split(":", 1)[1].strip()
        elif line.startswith("action:"):
            action = line.split(":", 1)[1].strip().lower()
        elif line.startswith("section:"):
            section = line.split(":", 1)[1].strip().strip("\"'")

    return Block(path=path, action=action, section=section, content=content)


# ═══════════════════════════════════════════════════════════════════════════════
# Block applicator
# ═══════════════════════════════════════════════════════════════════════════════

def apply_block(block: Block, vault_root: str, dry_run: bool = False) -> str:
    full_path = Path(vault_root) / block.path
    if block.action == "create":
        return action_create(full_path, block.content, dry_run)
    elif block.action == "append":
        return action_append(full_path, block.content, block.section, dry_run)
    elif block.action == "replace-section":
        return action_replace_section(full_path, block.content, block.section, dry_run)
    else:
        return f"Unknown action '{block.action}' for {block.path}"


def action_create(path: Path, content: str, dry_run: bool = False) -> str:
    if path.exists():
        return f"Skipped (already exists): {path}"
    if dry_run:
        return f"[DRY RUN] Would create: {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Created: {path}"


def action_append(path: Path, content: str, section: str | None, dry_run: bool = False) -> str:
    if dry_run:
        return f"[DRY RUN] Would append to {path} (section: {section})"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(_default_template_for(path, section), encoding="utf-8")

    existing = path.read_text(encoding="utf-8")
    if section and section in existing:
        parts = existing.split(section, 1)
        after_header = parts[1]
        next_idx = _find_next_section(after_header)
        if next_idx >= 0:
            new_content = parts[0] + section + after_header[:next_idx] + content + "\n" + after_header[next_idx:]
        else:
            new_content = parts[0] + section + after_header + content + "\n"
    elif section:
        new_content = existing.rstrip() + f"\n\n{section}\n\n{content}\n"
    else:
        new_content = existing.rstrip() + "\n" + content + "\n"

    path.write_text(new_content, encoding="utf-8")
    return f"Updated: {path}"


def action_replace_section(path: Path, content: str, section: str | None, dry_run: bool = False) -> str:
    if not section:
        return f"replace-section requires a section header for {path}"
    if dry_run:
        return f"[DRY RUN] Would replace section '{section}' in {path}"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{section}\n\n{content}\n", encoding="utf-8")
        return f"Created (with section): {path}"

    existing = path.read_text(encoding="utf-8")
    if section in existing:
        parts = existing.split(section, 1)
        after = parts[1]
        next_idx = _find_next_section(after)
        if next_idx >= 0:
            new_content = parts[0] + section + "\n" + content + "\n" + after[next_idx:]
        else:
            new_content = parts[0] + section + "\n" + content + "\n"
    else:
        new_content = existing.rstrip() + f"\n\n{section}\n\n{content}\n"

    path.write_text(new_content, encoding="utf-8")
    return f"Replaced section '{section}' in {path}"


def _find_next_section(text: str) -> int:
    m = re.search(r"\n## ", text)
    return m.start() if m else -1


# ═══════════════════════════════════════════════════════════════════════════════
# Default templates (per obsidian-note-framework.md)
# ═══════════════════════════════════════════════════════════════════════════════

def _default_template_for(path: Path, section: str | None) -> str:
    name = path.stem
    date = today_str()

    if "Daily/" in str(path):
        return f"""---
date: {date}
tags: [daily]
---

# {date}

## Sessions

| 时间 | 项目 | 做了什么 | 时长 |
|------|------|----------|------|

## Wins Today

-

## Blockers

-

## Notes

"""
    elif "Projects/" in str(path):
        return f"""---
status: active
created: {date}
updated: {date}
tech: []
tags: [project]
---

# {name}

## Overview

> One paragraph description of what this project is and why it exists.

## Tech Stack

| 类别 | 技术 |
|------|------|

## Changelog

<!-- Newest first, prepended by notes-skill -->

## Open Issues

<!-- Aggregated from all sessions -->

## Related Sessions

<!-- All sessions, newest first -->

## Knowledge Nodes

<!-- All knowledge nodes used in this project -->
"""
    elif "Sessions/" in str(path):
        return f"""---
date: {date}
time: {time_now()}
duration: unknown
project: unknown
type: coding
tags: []
---

# {date} {time_now()} · Unknown · Session

## 📁 项目

<!-- [[Projects/...]] -->

## ✏️ 修改了什么

### 新增

-

### 修改

-

### 删除

-

## 💬 对话摘要

<!-- 2-3 sentences -->

## 🔗 涉及的知识点

| 知识点 | 关系 | 备注 |
|--------|------|------|

## ❓ 遗留问题

- [ ]

## ✅ 本次收获

-
"""
    elif "Knowledge/" in str(path):
        return f"""---
type: concept
tags: []
first_seen: {date}
---

# {name}

## 一句话

<!-- one-line what and why -->

## 核心机制

-

## 代码片段

```python
# TODO: minimal working example
```

## 与其他概念的关系

- 父概念：
- 同类机制：
- 在项目中使用：

## 踩坑记录

| 日期 | 问题 | 解决方式 |
|------|------|----------|

## 来源会话

<!-- [[Sessions/...]] -->
"""
    elif "Meta/" in str(path) and "Knowledge-Graph" in str(path):
        return """---
tags: [meta, graph]
---

# Knowledge Graph

所有知识节点之间的关系表。

## 关系表

| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|

## 关系类型

| Relation | Meaning |
|----------|---------|
| `used-in` | Knowledge node used in a project |
| `parent-of` | Parent concept → child concept |
| `related-to` | Two knowledge nodes are related |
| `evolved-from` | Project built on top of an earlier one |
| `shares-stack-with` | Two projects share ≥2 tech items |
"""
    elif "Meta/" in str(path) and "Projects-Index" in str(path):
        return """---
tags: [meta, index]
---

# Projects Index

所有项目的总览表。

| Project | Status | Tech | Updated |
|---------|--------|------|---------|
"""
    else:
        return f"---\ntags: []\ncreated: {date}\n---\n\n# {name}\n"


# ═══════════════════════════════════════════════════════════════════════════════
# JSON pipeline — backward-compatible with parse_session.py output
# ═══════════════════════════════════════════════════════════════════════════════

def process_json(data: dict, vault_path: str, dry_run: bool = False) -> list[str]:
    results: list[str] = []
    date_str = data.get("date", today_str())
    project = data.get("project_name", "通用")

    # 1. Daily Note
    results.append(_write_daily_note(vault_path, data, date_str, dry_run))

    # 2. Project Note
    results.append(_write_project_note(vault_path, data, date_str, dry_run))

    # 3. Knowledge Nodes (unified — replaces snippets, concepts, tech cards, ADRs)
    for nt in data.get("note_types", []):
        if nt.get("type") == "knowledge_node":
            try:
                results.append(_write_knowledge_node(vault_path, nt, date_str, project, dry_run))
            except Exception as e:
                results.append(f"Error writing knowledge node '{nt.get('name')}': {e}")

    # 4. Knowledge Graph
    results.extend(_update_knowledge_graph(vault_path, data, date_str, dry_run))

    # 5. Projects Index
    results.append(_write_projects_index(vault_path, data, date_str, dry_run))

    # 6. Cross-project relations
    results.extend(_infer_cross_project_relations(vault_path, data, date_str, dry_run))

    return results


# ── Daily Note (table format) ─────────────────────────────────────────────────

def _write_daily_note(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> str:
    daily_path = Path(vault_path) / "Daily" / f"{date_str}.md"
    _ensure_file(daily_path, _default_template_for(daily_path, None))

    project = data.get("project_name", "通用")
    topic = data.get("session_topic", "Session")
    session_time = data.get("session_time", time_now())
    duration = "~session"

    # Table row format: | 时间 | 项目 | 做了什么 | 时长 |
    row = f"| {session_time} | [[Projects/{project}]] | {topic[:60]} | {duration} |"

    if dry_run:
        return f"[DRY RUN] Would append row to Sessions table in {daily_path}"

    content = daily_path.read_text(encoding="utf-8")

    # Append row to the Sessions table (after the header separator line)
    if "## Sessions" in content:
        # Find the table header separator (|---|---|...) after ## Sessions
        sessions_start = content.find("## Sessions")
        after_sessions = content[sessions_start:]
        separator_match = re.search(r"\|[-| ]+\|", after_sessions)
        if separator_match:
            insert_at = sessions_start + separator_match.end()
            new_content = content[:insert_at] + "\n" + row + content[insert_at:]
        else:
            # No table yet — create it
            table_header = "\n| 时间 | 项目 | 做了什么 | 时长 |\n|------|------|----------|------|\n"
            parts = content.split("## Sessions", 1)
            new_content = parts[0] + "## Sessions" + table_header + row + parts[1]
    else:
        # No Sessions section — add before Wins
        table = f"## Sessions\n\n| 时间 | 项目 | 做了什么 | 时长 |\n|------|------|----------|------|\n{row}\n\n"
        if "## Wins Today" in content:
            new_content = content.replace("## Wins Today", table + "## Wins Today")
        else:
            new_content = content.rstrip() + "\n\n" + table

    daily_path.write_text(new_content, encoding="utf-8")
    return f"Updated {daily_path}"


# ── Project Note (Changelog format) ───────────────────────────────────────────

def _write_project_note(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> str:
    project = data.get("project_name", "通用")
    proj_path = Path(vault_path) / "Projects" / f"{project}.md"
    _ensure_file(proj_path, _default_template_for(proj_path, None))

    topic = data.get("session_topic", "Session")
    summary = data.get("summary", "No summary.")
    changes = data.get("changes", [])
    session_time = data.get("session_time", "0000")
    session_file = f"{date_str}-{session_time}"
    open_issues = data.get("open_issues", [])
    open_str = ", ".join(open_issues) if open_issues else "none"

    files_list = " ".join(f"`{c.split(' — ')[0] if ' — ' in c else c[:40]}`" for c in changes[:5]) if changes else "—"

    entry = f"""### {date_str} · {topic[:80]}

> [[Sessions/{session_file}]] · ~session

{summary[:300]}

**修改文件：** {files_list}
**遗留：** {open_str}

---
"""

    if dry_run:
        return f"[DRY RUN] Would update {proj_path}"

    content = proj_path.read_text(encoding="utf-8")

    # Prepend to ## Changelog
    if "## Changelog" in content:
        parts = content.split("## Changelog", 1)
        after = parts[1]
        new_content = parts[0] + "## Changelog\n\n" + entry + after.lstrip("\n")
    else:
        new_content = content + "\n## Changelog\n\n" + entry

    # Update frontmatter
    new_content = re.sub(r"updated:\s*[\d-]+", f"updated: {date_str}", new_content, count=1)

    # Merge tech stack into Knowledge Nodes section
    tech_stack = data.get("tech_stack", {})
    if tech_stack:
        all_techs = []
        for techs in tech_stack.values():
            all_techs.extend(techs)
        for tech in all_techs:
            if f"[[Knowledge/{tech}]]" not in new_content:
                if "## Knowledge Nodes" in new_content:
                    new_content = new_content.replace(
                        "## Knowledge Nodes\n",
                        f"## Knowledge Nodes\n[[Knowledge/{tech}]] · ",
                    )

    proj_path.write_text(new_content, encoding="utf-8")
    return f"Updated {proj_path}"


# ── Knowledge Node (unified) ──────────────────────────────────────────────────

def _write_knowledge_node(vault_path: str, node: dict, date_str: str, project: str, dry_run: bool = False) -> str:
    tech_name = node.get("name", "Unknown")
    node_path = Path(vault_path) / "Knowledge" / f"{tech_name}.md"

    if dry_run:
        return f"[DRY RUN] Would {'update' if node_path.exists() else 'create'} knowledge node: {node_path}"

    node_path.parent.mkdir(parents=True, exist_ok=True)

    if node_path.exists():
        # Merge: append to "踩坑记录" table + "来源会话" only
        content = node_path.read_text(encoding="utf-8")
        session_file = f"{date_str}-{time_now()}"

        # Append pitfalls
        for pitfall in node.get("pitfalls", []):
            if pitfall not in content:
                pitfall_row = f"| {date_str} | {pitfall} | — |"
                if "## 踩坑记录" in content:
                    # Append after the table header
                    parts = content.split("## 踩坑记录", 1)
                    after = parts[1]
                    sep_match = re.search(r"\|[-| ]+\|", after)
                    if sep_match:
                        insert_at = len(parts[0]) + len("## 踩坑记录") + sep_match.end()
                        content = content[:insert_at] + "\n" + pitfall_row + content[insert_at:]

        # Append source session
        session_link = f"[[Sessions/{session_file}]]"
        if session_link not in content:
            if "## 来源会话" in content:
                content = content.replace("## 来源会话\n", f"## 来源会话\n{session_link}\n")
            else:
                content += f"\n## 来源会话\n{session_link}\n"

        node_path.write_text(content, encoding="utf-8")
        return f"Updated {node_path}"
    else:
        node_type = node.get("node_type", "concept")
        code_blocks = node.get("code_blocks", [])
        code_section = ""
        if code_blocks:
            lang = code_blocks[0].get("language", "python")
            code = code_blocks[0].get("code", "# TODO")
            code_section = "## 代码片段\n\n```{}\n{}\n```".format(lang, code)

        fallback_desc = "{} — {}".format(tech_name, node_type)
        fallback_code = "## 代码片段\n\n```python\n# TODO: minimal working example\n```"
        description = node.get("description", fallback_desc)
        code_block = code_section or fallback_code

        template = """---
type: {node_type}
tags: []
first_seen: {date_str}
---

# {tech_name}

## 一句话

{description}

## 核心机制

-

{code_block}

## 与其他概念的关系

- 父概念：
- 同类机制：
- 在项目中使用：[[Projects/{project}]]

## 踩坑记录

| 日期 | 问题 | 解决方式 |
|------|------|----------|

## 来源会话

[[Sessions/{date_str}-{time}]]
""".format(
            node_type=node_type,
            date_str=date_str,
            tech_name=tech_name,
            description=description,
            code_block=code_block,
            project=project,
            time=time_now(),
        )
        node_path.write_text(template, encoding="utf-8")
        return f"Created {node_path}"


# ── Knowledge Graph ───────────────────────────────────────────────────────────

def _update_knowledge_graph(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> list[str]:
    graph_path = Path(vault_path) / "Meta" / "Knowledge-Graph.md"
    if not graph_path.exists():
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(_default_template_for(graph_path, None), encoding="utf-8")

    project = data.get("project_name", "通用")
    tech_stack = data.get("tech_stack", {})
    session_file = f"{date_str}-{data.get('session_time', '0000')}"

    new_edges = []
    for _category, techs in tech_stack.items():
        for tech in techs:
            new_edges.append(
                f"| [[Knowledge/{tech}]] | used-in | [[Projects/{project}]] | {date_str} | [[Sessions/{session_file}]] |"
            )

    if dry_run:
        return [f"[DRY RUN] Would add {len(new_edges)} edges to Knowledge Graph"]

    content = graph_path.read_text(encoding="utf-8")
    existing_edges = set()
    for line in content.split("\n"):
        if line.startswith("| ") and " | " in line:
            parts = line.split(" | ")
            if len(parts) >= 3:
                src = parts[0].strip("| ").replace("[[", "").replace("]]", "")
                rel = parts[1].strip()
                tgt = parts[2].strip().replace("[[", "").replace("]]", "")
                existing_edges.add((src, rel, tgt))

    added = 0
    for edge in new_edges:
        parts = edge.split(" | ")
        if len(parts) >= 3:
            src = parts[0].strip("| ").replace("[[", "").replace("]]", "")
            rel = parts[1].strip()
            tgt = parts[2].strip().replace("[[", "").replace("]]", "")
            if (src, rel, tgt) not in existing_edges:
                content += edge + "\n"
                existing_edges.add((src, rel, tgt))
                added += 1

    graph_path.write_text(content, encoding="utf-8")
    return [f"Added {added} new edges to Knowledge Graph (skipped {len(new_edges) - added} duplicates)"]


# ── Projects Index ────────────────────────────────────────────────────────────

def _write_projects_index(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> str:
    index_path = Path(vault_path) / "Meta" / "Projects-Index.md"
    _ensure_file(index_path, _default_template_for(index_path, None))

    project = data.get("project_name", "通用")
    tech_stack = data.get("tech_stack", {})
    all_techs = []
    for techs in tech_stack.values():
        all_techs.extend(techs)
    tech_str = ", ".join(all_techs[:5]) if all_techs else "—"

    row = f"| [[Projects/{project}]] | active | {tech_str} | {date_str} |"

    if dry_run:
        return f"[DRY RUN] Would update Projects Index with: {row}"

    content = index_path.read_text(encoding="utf-8")

    if f"| [[Projects/{project}]] |" in content:
        # Update existing row
        for line in content.split("\n"):
            if f"| [[Projects/{project}]] |" in line:
                # Update date and tech
                new_line = re.sub(r"\|\s*[\d-]+\s*\|", f"| {date_str} |", line)
                new_line = re.sub(r"\|\s*[^|]+\s*\|\s*[\d-]+\s*\|$", f"| {tech_str} | {date_str} |", new_line)
                content = content.replace(line, new_line)
                break
    else:
        # Append new row after the table header
        sep_match = re.search(r"\|[-| ]+\|", content)
        if sep_match:
            insert_at = sep_match.end()
            content = content[:insert_at] + "\n" + row + content[insert_at:]
        else:
            content += row + "\n"

    index_path.write_text(content, encoding="utf-8")
    return f"Updated {index_path}"


# ── Cross-Project Relations ───────────────────────────────────────────────────

def _infer_cross_project_relations(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> list[str]:
    projects_dir = Path(vault_path) / "Projects"
    if not projects_dir.exists():
        return ["No Projects/ directory — skipping cross-project inference."]

    current_project = data.get("project_name", "通用")
    current_tech = set()
    for techs in data.get("tech_stack", {}).values():
        current_tech.update(t.lower() for t in techs)

    if not current_tech or current_project == "通用":
        return ["Skipping cross-project inference (no tech or generic project)."]

    results = []
    for proj_file in projects_dir.glob("*.md"):
        proj_name = proj_file.stem
        if proj_name == current_project:
            continue
        proj_content = proj_file.read_text(encoding="utf-8")
        proj_tech = set()
        for line in proj_content.split("\n"):
            if line.startswith("| ") and " | " in line:
                techs_in_row = re.findall(r"`?(\w[\w\s-]+\w)`?", line)
                for t in techs_in_row:
                    t = t.strip()
                    if t not in ("Category", "Technologies", "Language", "Framework",
                                  "Tool", "API", "Library", "Concept", "类别", "技术") and len(t) > 1:
                        proj_tech.add(t.lower())

        overlap = current_tech & proj_tech
        if len(overlap) >= 2:
            results.append({"target": proj_name, "relation": "shares-stack-with",
                            "detail": f"({', '.join(sorted(overlap)[:3])})"})

    if results and not dry_run:
        proj_path = projects_dir / f"{current_project}.md"
        if proj_path.exists():
            content = proj_path.read_text(encoding="utf-8")
            if "## Related Sessions" in content:
                for rel in results:
                    rel_line = f"- [[{rel['target']}]] — `{rel['relation']}` {rel['detail']}"
                    if rel_line not in content:
                        parts = content.split("## Related Sessions", 1)
                        after = parts[1]
                        next_idx = _find_next_section(after)
                        if next_idx >= 0:
                            content = parts[0] + "## Related Sessions" + after[:next_idx] + rel_line + "\n" + after[next_idx:]
                        else:
                            content = parts[0] + "## Related Sessions\n" + rel_line + "\n" + after
            proj_path.write_text(content, encoding="utf-8")

    if dry_run:
        return [f"[DRY RUN] Would infer {len(results)} cross-project relations"]
    return [f"Inferred {len(results)} cross-project relations"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_file(path: Path, template: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template, encoding="utf-8")


def _slugify(text: str) -> str:
    return re.sub(r"[^\w\-]+", "-", text.lower())[:60]


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    vault_path: str | None = None
    input_path: str | None = None
    dry_run = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--vault" and i + 1 < len(args):
            vault_path = args[i + 1]
            i += 2
        elif args[i].startswith("--vault="):
            vault_path = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--input" and i + 1 < len(args):
            input_path = args[i + 1]
            i += 2
        elif args[i].startswith("--input="):
            input_path = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            i += 1

    if not vault_path:
        try:
            config = load_config()
            vault_path = config["vault_path"]
        except (SystemExit, KeyError):
            print("Usage: python scripts/sync.py --vault <path> --input <file> [--dry-run]", file=sys.stderr)
            print("       Or set vault_path in config/vault_config.json", file=sys.stderr)
            sys.exit(1)

    if input_path:
        input_text = Path(input_path).read_text(encoding="utf-8")
    else:
        input_text = sys.stdin.read()

    if not input_text.strip():
        print("No input provided.", file=sys.stderr)
        sys.exit(1)

    results: list[str] = []

    if input_text.strip().startswith("{"):
        data = json.loads(input_text)
        results = process_json(data, vault_path, dry_run)
    else:
        blocks = parse_blocks(input_text)
        if not blocks:
            print("No obsidian-file blocks found in input.", file=sys.stderr)
            sys.exit(1)
        for block in blocks:
            results.append(apply_block(block, vault_path, dry_run))

    print("\n".join(results))
    if not dry_run:
        print(f"\nVault updated: {vault_path}")


if __name__ == "__main__":
    main()
