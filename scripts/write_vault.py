#!/usr/bin/env python3
"""Write extracted knowledge into an Obsidian vault.

Reads the extraction JSON and writes/updates:
  - Daily Note: append to ## AI Sessions
  - Project Note: prepend to ## Session Log, update ## Tech Stack
  - Tech Stack Index: merge entries
  - QA Archive: append problem-solution entries
  - Snippets, Concept Notes, Tech Cards, ADRs (from note_types field)

Usage:
    python scripts/write_vault.py --input /tmp/extracted.json
    python scripts/write_vault.py --input extracted.json --dry-run
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "vault_config.json"


def load_config() -> dict:
    """Load vault configuration."""
    if not CONFIG_FILE.exists():
        print(f"Config not found: {CONFIG_FILE}", file=sys.stderr)
        print("Run `python scripts/setup.py` first.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def today_str(fmt: str = "YYYY-MM-DD") -> str:
    """Return today's date string."""
    now = datetime.now(timezone.utc)
    # Support both ISO and YYYY-MM-DD
    if fmt == "YYYY-MM-DD":
        return now.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


def ensure_file(path: Path, template: str) -> None:
    """Create file from template if it doesn't exist."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template, encoding="utf-8")


def daily_note_template(date_str: str) -> str:
    """Daily Note Markdown template."""
    return f"""---
tags: [daily]
date: {date_str}
---

# {date_str}

## Focus
> What matters most today?

-

## Today's Progress
- [ ]

## AI Sessions

<!-- Sessions appended here by agent-knowledge -->

## Action Items
- [ ]

## Notes & Thoughts

---
*Created by agent-knowledge*
"""


def project_note_template(project_name: str, date_str: str) -> str:
    """Project Note Markdown template."""
    return f"""---
tags: [project]
status: active
created: {date_str}
updated: {date_str}
tech: []
---

# {project_name}

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
*Last synced: {date_str}*
"""


def tech_index_template() -> str:
    """Tech Stack Index template."""
    return """---
tags: [meta, index]
---

# Tech Stack Index

Cross-project technology index. One section per technology.

<!-- Entries merged here by agent-knowledge -->
"""


def qa_archive_template() -> str:
    """QA Archive template."""
    return """---
tags: [meta, archive]
---

# QA Archive

Problem-solution pairs collected across all projects.

<!-- Entries appended here by agent-knowledge -->
"""


def write_daily_note(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> str:
    """Append a session entry to the Daily Note."""
    daily_path = Path(vault_path) / "Daily" / f"{date_str}.md"
    ensure_file(daily_path, daily_note_template(date_str))

    # Build the callout block
    tech_tags = ", ".join(
        tech for techs in data.get("tech_stack", {}).values() for tech in techs
    )
    tags = " ".join(
        f"#{t}" for t in _tags_from_tech(data.get("tech_stack", {}))
    ) or "#session"

    project = data.get("project_name", "通用")
    topic = data.get("session_topic", "Session")

    entry = f"""
> [!summary]- {topic} · [[{project}]]
> {data.get('summary', 'No summary.')}
> **Tech**: {tech_tags or 'none'}
> **Tags**: {tags}
"""

    if dry_run:
        return f"[DRY RUN] Would append to {daily_path}:\n{entry}"

    content = daily_path.read_text(encoding="utf-8")

    # Find ## AI Sessions section and append
    if "## AI Sessions" in content:
        # Append after the ## AI Sessions header, before next ## section
        parts = content.split("## AI Sessions", 1)
        after_header = parts[1]
        # Find next ## section
        next_section_idx = _find_next_section(after_header)
        if next_section_idx >= 0:
            new_content = (
                parts[0]
                + "## AI Sessions"
                + after_header[:next_section_idx]
                + entry
                + "\n"
                + after_header[next_section_idx:]
            )
        else:
            new_content = parts[0] + "## AI Sessions" + after_header + entry + "\n"
    else:
        # Insert ## AI Sessions section before ## Action Items or at end
        if "## Action Items" in content:
            new_content = content.replace(
                "## Action Items",
                "## AI Sessions\n" + entry + "\n## Action Items",
            )
        else:
            new_content = content + "\n## AI Sessions\n" + entry + "\n"

    daily_path.write_text(new_content, encoding="utf-8")
    return f"Updated {daily_path}"


def _find_next_section(text: str) -> int:
    """Find the index of the next ## heading in text."""
    import re
    m = re.search(r"\n## ", text)
    return m.start() if m else -1


def write_project_note(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> str:
    """Prepend a session log entry to the Project Note and update tech stack."""
    project = data.get("project_name", "通用")
    project_path = Path(vault_path) / "Projects" / f"{project}.md"
    ensure_file(project_path, project_note_template(project, date_str))

    topic = data.get("session_topic", "Session")
    summary = data.get("summary", "No summary.")
    changes = data.get("changes", [])
    open_issues = data.get("open_issues", [])
    open_str = ", ".join(open_issues) if open_issues else "none"

    changes_list = "\n".join(f"- {c}" for c in changes) if changes else "- (none)"

    session_entry = f"""### {date_str} · {topic}
> [[Daily/{date_str}]] · ~session

{summary}

**Changes**:
{changes_list}

**Open Issues**: {open_str}

"""

    if dry_run:
        return f"[DRY RUN] Would update {project_path} with session entry"

    content = project_path.read_text(encoding="utf-8")

    # Prepend to ## Session Log
    if "## Session Log" in content:
        parts = content.split("## Session Log", 1)
        after_header = parts[1]
        new_content = parts[0] + "## Session Log\n\n" + session_entry + after_header.lstrip("\n")
    else:
        new_content = content + "\n## Session Log\n\n" + session_entry

    # Update frontmatter updated: date
    new_content = _update_frontmatter_date(new_content, date_str)

    # Update Tech Stack table in the project note
    new_content = _merge_tech_stack_table(new_content, data.get("tech_stack", {}))

    project_path.write_text(new_content, encoding="utf-8")
    return f"Updated {project_path}"


def _update_frontmatter_date(content: str, date_str: str) -> str:
    """Update the `updated:` field in YAML frontmatter."""
    import re
    return re.sub(r"updated:\s*[\d-]+", f"updated: {date_str}", content, count=1)


def _merge_tech_stack_table(content: str, tech_stack: dict[str, list[str]]) -> str:
    """Merge new tech entries into the Tech Stack markdown table in project note."""
    if not tech_stack:
        return content

    for category, techs in tech_stack.items():
        for tech in techs:
            # Check if tech already exists in the table
            if tech not in content:
                # Find the category row and append the tech
                # This is a best-effort text manipulation
                cat_pattern = f"| {category} |"
                if cat_pattern in content:
                    # Find the row and append tech
                    lines = content.split("\n")
                    new_lines = []
                    for line in lines:
                        new_lines.append(line)
                        if line.strip().startswith(f"| {category} |") and tech not in line:
                            # Append tech to this row
                            new_lines[-1] = new_lines[-1].rstrip() + f" · {tech}"
                    content = "\n".join(new_lines)

    return content


def write_tech_index(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> str:
    """Merge tech entries into the Tech Stack Index."""
    index_path = Path(vault_path) / "Meta" / "Tech Stack Index.md"
    ensure_file(index_path, tech_index_template())

    tech_stack = data.get("tech_stack", {})
    if not tech_stack:
        return "No tech stack to index."

    if dry_run:
        return f"[DRY RUN] Would merge tech entries into {index_path}"

    content = index_path.read_text(encoding="utf-8")
    project = data.get("project_name", "通用")

    for category, techs in tech_stack.items():
        for tech in techs:
            entry = f"""## {tech}
- Used in: [[{project}]]
- Last seen: {date_str}

"""
            if f"## {tech}" not in content:
                content += entry
            else:
                # Update Last seen date and add project if not listed
                # Simple regex-based update
                import re
                pattern = rf"(## {re.escape(tech)}\n- Used in: \[\[.*?\]\].*?\n- Last seen: )[\d-]+"
                if re.search(pattern, content):
                    content = re.sub(pattern, rf"\g<1>{date_str}", content)
                # Add project if missing
                section_start = content.find(f"## {tech}")
                if section_start >= 0:
                    next_section = content.find("\n## ", section_start + 1)
                    if next_section < 0:
                        next_section = len(content)
                    section = content[section_start:next_section]
                    if f"[[{project}]]" not in section:
                        # Add project to Used in line
                        old_used = f"## {tech}\n- Used in: "
                        new_used = f"## {tech}\n- Used in: [[{project}]], "
                        content = content.replace(old_used, new_used, 1)

    index_path.write_text(content, encoding="utf-8")
    return f"Updated {index_path}"


def write_qa_archive(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> str:
    """Append problem-solution entries to the QA Archive."""
    qa_path = Path(vault_path) / "Meta" / "QA Archive.md"
    ensure_file(qa_path, qa_archive_template())

    problems = data.get("problems_solved", [])
    if not problems:
        return "No Q&A entries to archive."

    if dry_run:
        return f"[DRY RUN] Would append {len(problems)} Q&A entries to {qa_path}"

    content = qa_path.read_text(encoding="utf-8")

    for p in problems:
        tags = " ".join(p.get("tags", [])) or "#general"
        entry = f"""### {p.get('title', 'Untitled')}
**Date**: {date_str}
**Context**: {p.get('context', 'N/A')}

**Problem**:
{p.get('problem', 'N/A')}

**Solution**:
{p.get('solution', 'N/A')}

**Tags**: {tags}

---
"""
        # Only append if not already present (dedup by title)
        if p.get("title") and f"### {p['title']}" not in content:
            content = entry + content  # newest first

    qa_path.write_text(content, encoding="utf-8")
    return f"Updated {qa_path}"


def _tags_from_tech(tech_stack: dict[str, list[str]]) -> list[str]:
    """Generate simple tags from tech stack categories."""
    tag_map = {
        "Language": "coding",
        "Framework": "framework",
        "Tool": "tools",
        "API": "api",
        "Library": "library",
        "Concept": "architecture",
    }
    tags = []
    for category in tech_stack:
        if category in tag_map:
            tags.append(tag_map[category])
    return sorted(set(tags))


# ── New note-type writers ────────────────────────────────────────────────────


def write_snippet(vault_path: str, snippet: dict, date_str: str, project: str, dry_run: bool = False) -> str:
    """Create a Snippet note for a reusable code block."""
    slug = re.sub(r"[^\w\-]+", "-", snippet.get("title", "snippet").lower())[:60]
    snippet_path = Path(vault_path) / "Snippets" / f"{slug}.md"

    template = f"""---
tags: [snippet]
tech: "[[{snippet.get('primary_tech', 'unknown')}]]"
context: "[[Projects/{project}]]"
date: {date_str}
works_on: []
type: snippet
---

# {snippet.get('title', 'Untitled Snippet')}

## 场景
{snippet.get('title', 'N/A')}

## 代码
```{snippet.get('language', 'text')}
{snippet.get('code', 'N/A')}
```

## 注意
{chr(10).join('- ' + c for c in snippet.get('caveats', [])) or '- (none)'}

## 来源
[[Sessions/{date_str}-TODO]]
"""

    if dry_run:
        return f"[DRY RUN] Would create snippet: {snippet_path}"

    if snippet_path.exists():
        return f"Skipped (already exists): {snippet_path}"

    snippet_path.parent.mkdir(parents=True, exist_ok=True)
    snippet_path.write_text(template, encoding="utf-8")
    return f"Created {snippet_path}"


def write_concept_note(vault_path: str, concept: dict, date_str: str, project: str, dry_run: bool = False) -> str:
    """Create a Zettelkasten Concept Note."""
    name = concept.get("name", "Unknown Concept")
    concept_path = Path(vault_path) / "Concepts" / f"{name}.md"

    related_links = " · ".join(f"[[{r}]]" for r in concept.get("related", []))

    template = f"""---
tags: [concept]
domain: [{concept.get('domain', 'general')}]
date: {date_str}
type: concept
---

# {name}

## 核心思想
{concept.get('core_idea', 'N/A')}

## 常见方式对比
| 方式 | 延迟 | 适用场景 |
|------|------|---------|
| | | |

## 我的理解
> Write in your own words — how would you explain this to a colleague?

## 在哪里用过
- [[Projects/{project}]] — {date_str}

## 关联概念
{related_links or '[[TODO]]'}

## 来源
[[Sessions/{date_str}-TODO]]
"""

    if dry_run:
        return f"[DRY RUN] Would {'update' if concept_path.exists() else 'create'} concept: {concept_path}"

    concept_path.parent.mkdir(parents=True, exist_ok=True)

    if concept_path.exists():
        # Merge strategy: ONLY append to "在哪里用过" and "来源" lists.
        # NEVER modify body sections (核心思想, 常见方式对比, 我的理解, 关联概念) —
        # those belong to the user. This prevents agent from overwriting manual edits.
        content = concept_path.read_text(encoding="utf-8")

        # Append project to "在哪里用过" if not already listed
        if f"[[{project}]]" not in content:
            usage_entry = f"- [[Projects/{project}]] — {date_str}\n"
            if "## 在哪里用过" in content:
                content = content.replace(
                    "## 在哪里用过\n",
                    f"## 在哪里用过\n{usage_entry}",
                )
            else:
                content += f"\n## 在哪里用过\n{usage_entry}"

        # Append session to "来源" if not already listed
        session_link = f"[[Sessions/{date_str}-TODO]]"
        if session_link not in content:
            if "## 来源" in content:
                content = content.replace(
                    "## 来源\n",
                    f"## 来源\n{session_link}\n",
                )
            else:
                content += f"\n## 来源\n{session_link}\n"

        concept_path.write_text(content, encoding="utf-8")
        return f"Updated {concept_path}"
    else:
        concept_path.write_text(template, encoding="utf-8")
        return f"Created {concept_path}"


def write_tech_card(vault_path: str, card: dict, date_str: str, project: str, dry_run: bool = False) -> str:
    """Create or update a Tech Card for a tool/framework/library."""
    tech_name = card.get("name", "Unknown Tech")
    tech_path = Path(vault_path) / "Tech" / f"{tech_name}.md"

    template = f"""---
tags: [tech-card]
type: technology
category: {card.get('category', 'unknown')}
status: {"learning" if card.get('is_first_use') else "active"}
first_used: {date_str}
last_used: {date_str}
---

# {tech_name}

## 一句话描述
{card.get('description', 'N/A')}

## 用过的版本
`{card.get('version') or 'unknown'}`

## 核心用法
```python
# TODO: add minimal working example
```

## 踩过的坑
{chr(10).join('- ' + p for p in card.get('new_pitfalls', [])) or '- (none yet)'}

## 参考资料
- (add links)

## 用在哪些项目
```dataview
LIST FROM [[]] WHERE contains(tech, "{tech_name}")
```

## 来源
[[Sessions/{date_str}-TODO]]
"""

    if dry_run:
        return f"[DRY RUN] Would {'update' if tech_path.exists() else 'create'} tech card: {tech_path}"

    tech_path.parent.mkdir(parents=True, exist_ok=True)

    if tech_path.exists():
        # Merge: update last_used, append new pitfalls, update version
        content = tech_path.read_text(encoding="utf-8")
        content = re.sub(r"last_used:\s*[\d-]+", f"last_used: {date_str}", content)

        if card.get("version"):
            content = re.sub(r"## 用过的版本\n`[^`]*`", f"## 用过的版本\n`{card['version']}`", content)

        for pitfall in card.get("new_pitfalls", []):
            if pitfall not in content:
                content = content.replace(
                    "## 踩过的坑",
                    f"## 踩过的坑\n- {pitfall}",
                )

        if f"[[{project}]]" not in content:
            content += f"\n- [[Projects/{project}]] — {date_str}\n"

        tech_path.write_text(content, encoding="utf-8")
        return f"Updated {tech_path}"
    else:
        tech_path.write_text(template, encoding="utf-8")
        return f"Created {tech_path}"


def write_adr(vault_path: str, adr: dict, date_str: str, project: str, dry_run: bool = False) -> str:
    """Create an Architecture Decision Record."""
    # Determine ADR number
    decisions_dir = Path(vault_path) / "Decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    existing = list(decisions_dir.glob("ADR-*.md"))
    adr_num = len(existing) + 1

    slug = re.sub(r"[^\w\-]+", "-", adr.get("title", "decision").lower())[:50]
    adr_path = decisions_dir / f"ADR-{adr_num:03d}-{slug}.md"

    options_text = ""
    for i, opt in enumerate(adr.get("options", []), 1):
        status = " ✅ 选中" if opt.get("status") == "chosen" else " ❌ 未选"
        options_text += f"{i}. {opt.get('name', 'Option ' + str(i))}{status}\n"

    reasons_text = "\n".join(f"- {r}" for r in adr.get("reasons", [])) or "- (see session log)"
    tradeoffs_text = "\n".join(f"- {t}" for t in adr.get("tradeoffs", [])) or "- (none noted)"

    template = f"""---
tags: [ADR]
project: "[[Projects/{project}]]"
date: {date_str}
status: accepted
superseded_by: null
type: decision
---

# ADR-{adr_num:03d} · {adr.get('title', 'Untitled Decision')}

## 背景
{adr.get('background', 'N/A')}

## 问题
{adr.get('problem', 'N/A')}

## 考虑的方案
{options_text}

## 决定
选方案 {adr.get('chosen', 'unknown')}。

## 原因
{reasons_text}

## 代价 / 权衡
{tradeoffs_text}

## 关联 session
[[Sessions/{date_str}-TODO]]

## 关联 ADR
<!-- Link superseded/superseding ADRs here -->
"""

    if dry_run:
        return f"[DRY RUN] Would create ADR: {adr_path}"

    adr_path.write_text(template, encoding="utf-8")
    return f"Created {adr_path}"


def write_note_types(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> list[str]:
    """Route extracted note_types to the appropriate writers."""
    results = []
    note_types = data.get("note_types", [])
    project = data.get("project_name", "通用")

    for nt in note_types:
        nt_type = nt.get("type", "")
        try:
            if nt_type == "snippet":
                results.append(write_snippet(vault_path, nt, date_str, project, dry_run))
            elif nt_type == "concept":
                results.append(write_concept_note(vault_path, nt, date_str, project, dry_run))
            elif nt_type == "tech_card":
                results.append(write_tech_card(vault_path, nt, date_str, project, dry_run))
            elif nt_type == "adr":
                results.append(write_adr(vault_path, nt, date_str, project, dry_run))
        except Exception as e:
            results.append(f"Error writing {nt_type} '{nt.get('name', nt.get('title', 'unknown'))}': {e}")

    return results


def main():
    input_path = None
    dry_run = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
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

    if not input_path:
        print("Usage: python scripts/write_vault.py --input <extracted.json> [--dry-run]", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    vault_path = config["vault_path"]
    date_fmt = config.get("date_format", "YYYY-MM-DD")
    date_str = today_str(date_fmt)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []

    # 1. Daily Note
    results.append(write_daily_note(vault_path, data, date_str, dry_run))

    # 2. Project Note
    results.append(write_project_note(vault_path, data, date_str, dry_run))

    # 3. Tech Stack Index
    results.append(write_tech_index(vault_path, data, date_str, dry_run))

    # 4. QA Archive
    results.append(write_qa_archive(vault_path, data, date_str, dry_run))

    # 5. Note types (snippets, concepts, tech cards, ADRs)
    results.extend(write_note_types(vault_path, data, date_str, dry_run))

    # Summary
    print("\n".join(results))
    if not dry_run:
        print(f"\nVault updated: {vault_path}")


if __name__ == "__main__":
    main()
