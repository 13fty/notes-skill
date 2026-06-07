---
name: notes-skill
description: >
  Auto-hook knowledge accumulation system. After every agent task (coding, debugging,
  design, research), automatically extract what was learned — new tech, bug fixes,
  project changes, design decisions — and persist structured notes into an Obsidian vault.
  Trigger on: every agent task completion, "记录一下", "保存到 obsidian", "更新笔记",
  "save this session", "log this to obsidian", "这次学到了什么", "整理到知识库",
  or any request to persist conversation content into a knowledge base.
  This skill should fire after substantial work is done, even without explicit user request.
license: MIT. See LICENSE.txt for complete terms
---

# Agent Knowledge Sync

Auto-hook system that extracts structured knowledge from agent task sessions and writes
interlinked notes into the user's Obsidian vault. Follows the **3-layer note framework**
from `obsidian-note-framework.md`: Session → Project → Knowledge.

## Vault Layout

```
{VaultRoot}/
├── Sessions/       ← ① Session logs (YYYY-MM-DD-HHMM.md)
├── Projects/       ← ② Project notes (Changelog-based)
├── Daily/          ← ② Daily notes (table-based Sessions list)
├── Knowledge/      ← ③ Unified knowledge nodes (concept|tool|framework|pattern)
└── Meta/           ← Knowledge-Graph.md + Projects-Index.md
```

## Prerequisites

```bash
python scripts/setup.py --json           # Discover vaults
python scripts/setup.py                  # Run setup wizard (first time only)
```

---

## The 8-Step Pipeline

### Step 1 — Generate Session Summary

Produce a one-line topic + 2-3 sentence summary (past tense). This becomes the
foundation for the Session Log, Daily Note table row, and Project Changelog entry.

### Step 2 — Update Daily Note

**Target**: `<vault>/Daily/YYYY-MM-DD.md`
**Operation**: Append a row to the `## Sessions` table

```markdown
| 时间 | 项目 | 做了什么 | 时长 |
|------|------|----------|------|
| 14:30 | [[Projects/MyApp]] | Fixed Docker build by adding pydantic | 52min |
```

See `references/templates.md` § Template: Daily Note.

### Step 3 — Update Project Note

**Target**: `<vault>/Projects/{ProjectName}.md`
**Operation**: Prepend an entry to `## Changelog`, update frontmatter, merge tech into `## Knowledge Nodes`

```markdown
### YYYY-MM-DD · Topic
> [[Sessions/YYYY-MM-DD-HHMM]] · ~duration

Summary paragraph.

**修改文件：** `file1.py` `file2.swift`
**遗留：** issue description or none
```

See `references/templates.md` § Template: Project Note.

### Step 4 — Extract Tech Stack & Create Knowledge Nodes

**Script**: `python scripts/parse_session.py --session-text "..."`

Detects technologies in 6 categories (Language, Framework, Tool, API, Library, Concept).

For each technology found, create or update a **Knowledge Node** in `<vault>/Knowledge/{TechName}.md`:
- New tech → create from template with `first_seen` date
- Existing tech → append to "踩过的坑" (pitfall table) and "来源会话" (source sessions)

Also append `[[Knowledge/{TechName}]]` links to the Project Note's `## Knowledge Nodes` section.

See `references/templates.md` § Template: Knowledge Node and § Tech Classification Rules.

### Step 5 — Extract Q&A Pairs

**Script**: `python scripts/parse_session.py --session-text "..."`

Paragraph-based matching with Chinese + English signal words. Detected Q&A pairs are
integrated into:
- Session Log's `## 🔗 涉及的知识点` table (as rows)
- Session Log's `## ❓ 遗留问题` (if unresolved)
- Knowledge Node's `## 踩坑记录` table (if a specific tech was involved)

### Step 6 — Auto-Generate Wiki Links

**Function**: `linkify()` in `scripts/parse_session.py`

| Condition | Conversion |
|-----------|------------|
| Date `YYYY-MM-DD` | `[[Daily/YYYY-MM-DD]]` |
| Known project name | `[[Projects/ProjectName]]` |
| Tech from TECH_REGISTRY | `[[Knowledge/TechName]]` |

Rules: first occurrence only, longest-match-first for project names.

### Step 7 — Infer Project Relations

Scan existing project notes. If tech overlap ≥2 → `shares-stack-with`.
Also detect `evolved-from`, `inspired-by`, `depends-on` from conversation context.

Write to Project Note's `## Related Sessions` and Knowledge Graph.

### Step 8 — Maintain Knowledge Graph

- **`Meta/Knowledge-Graph.md`**: Append `used-in` edges (Knowledge → Project), dedup by triple
- **`Meta/Projects-Index.md`**: Merge project row (update date + tech list)

Edge format:
```markdown
| [[Knowledge/Python]] | used-in | [[Projects/MyApp]] | 2026-06-07 | [[Sessions/2026-06-07-1430]] |
```

See `references/templates.md` § Template: Knowledge Graph and § Template: Projects Index.

---

## Session Log — The Most Important File

Every agent session produces a Session Log at `Sessions/YYYY-MM-DD-HHMM.md`
(see `references/templates.md` § Template: Session Log):

- `## 📁 项目` — Project link + modified files
- `## ✏️ 修改了什么` — 新增 / 修改 / 删除
- `## 💬 对话摘要` — 2-3 sentence narrative
- `## 🔗 涉及的知识点` — Knowledge node table (知识点 / 关系 / 备注)
- `## ❓ 遗留问题` — Open issues checkbox list
- `## ✅ 本次收获` — Key takeaways

---

## obsidian-file Block Format

````markdown
```obsidian-file
path: Sessions/2026-06-07-1430.md
action: create
---
(entire file content)
```

```obsidian-file
path: Daily/2026-06-07.md
action: append
section: ## Sessions
---
| 14:30 | [[Projects/notes-skill]] | Refactored note structure | 45min |
```

```obsidian-file
path: Projects/notes-skill.md
action: append
section: ## Changelog
---
### 2026-06-07 · Refactored note structure
...
```
````

Write blocks to a temp file and run:

```bash
python scripts/sync.py --input /tmp/sync_output.md
```

---

## Quick Reference

| Task | Resource |
|------|----------|
| Read vault config | `config/vault_config.json` |
| Parse session into structured JSON | `python scripts/parse_session.py --session-text "..."` |
| Write obsidian-file blocks to vault | `python scripts/sync.py --input output.md` |
| JSON pipeline (backward compat) | `python scripts/sync.py --input parsed.json` |
| Setup wizard | `python scripts/setup.py` |
| All templates + classification rules | `references/templates.md` |
| Framework design document | `obsidian-note-framework.md` |

---

## Output Checklist

- [ ] **Step 1**: Session summary generated (one-liner + 2-3 sentences, past tense)
- [ ] **Step 2**: Daily Note Sessions table row appended (时间/项目/做了什么/时长)
- [ ] **Step 3**: Project Note Changelog entry prepended (with file list + open issues)
- [ ] **Step 4**: Knowledge nodes created/updated in `Knowledge/` + Project Note `## Knowledge Nodes` updated
- [ ] **Step 5**: Q&A pairs integrated into Session Log (涉及的知识点 + 遗留问题)
- [ ] **Step 6**: All proper nouns Wiki-linked (dates → Daily/, projects → Projects/, tech → Knowledge/)
- [ ] **Step 7**: Cross-project relations inferred (tech overlap ≥2)
- [ ] **Step 8**: Knowledge-Graph.md edges appended + Projects-Index.md row merged

---

## Auto-Trigger Heuristics

Fire when an agent session has produced substantive work:

- ≥3 tool calls completed
- Code was written, edited, or debugged
- A bug was fixed or a feature was implemented
- New technologies or libraries were introduced
- User explicitly asked to record/save

Do NOT fire for: single-question answers, conversational chat, trivial file reads.

## Dependencies

- Python 3.9+ (stdlib only — no pip packages required)
- Obsidian vault with `.obsidian` directory
- Write access to vault path
