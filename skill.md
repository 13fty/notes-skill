---
name: obsidian
description: >
  Process AI agent conversation sessions and sync structured knowledge into Obsidian vaults.
  Use this skill whenever the user wants to: summarize an AI/Claude conversation into Obsidian notes,
  update a Daily Note or Project Note with session insights, extract tech stacks or Q&A from a chat,
  create Wiki Links between notes, build project associations, or maintain a knowledge graph in Obsidian.
  Trigger on phrases like "save to obsidian", "update my notes", "log this session", "add to daily note",
  "extract tech stack", "create wiki links", "update project note", or any request to persist
  conversation content into an Obsidian vault. Even if the user just says "记录一下" or "整理笔记",
  treat it as a potential Obsidian sync task.
---

# Obsidian Knowledge Sync Skill

This skill processes AI agent conversation sessions and writes structured, interlinked Markdown notes
into an Obsidian vault. It handles eight core capabilities.

## Workflow Overview

```
Input: Conversation transcript / session summary
         │
         ▼
    1. Summarize Session
         │
         ├──► 2. Update Daily Note
         ├──► 3. Update Project Note
         ├──► 4. Extract Tech Stack  ──────────────────► Tech Stack Index
         ├──► 5. Extract Q&A Pairs   ──────────────────► Q&A Archive
         ├──► 6. Generate Wiki Links ─────────────────┐
         ├──► 7. Project Associations ────────────────┤
         └──► 8. Knowledge Graph Edges ───────────────┘
                                                       │
                                                       ▼
                                              Final Linked Note Set
```

---

## Step 1 — Summarize AI Agent Session

Before writing any note, produce a **Session Summary** from the conversation input.

### Summary Schema

```markdown
## Session Summary · {YYYY-MM-DD HH:mm}

**主题**: {one-line topic}
**项目**: {project name, or "通用"}
**持续时间**: {estimated, e.g. "~45 min"}
**核心产出**: {bullet list, max 5 items}
**未解决问题**: {bullet list, or "无"}
**下一步行动**: {bullet list with owner/deadline if known}
```

Rules:
- Keep it ≤ 20 lines
- Use past tense ("解决了", "实现了")
- Never include raw code blocks in the summary itself; those go in Project Note sections

---

## Step 2 — Update Daily Note

**File path pattern**: `{vault}/Daily/{YYYY-MM-DD}.md`

### Insertion Strategy

1. Read existing Daily Note if it exists; otherwise create from template (see `templates/daily.md`)
2. Find or create the `## AI Sessions` section
3. Append a collapsible block:

```markdown
## AI Sessions

> [!summary]- {HH:mm} · {Session Topic} · [[{ProjectName}]]
> {Session Summary from Step 1}
> 
> **Tech**: {comma-separated tech tags}
> **Tags**: #{tag1} #{tag2}
```

4. Update the `## Today's Progress` checklist if present — check off completed items that match session outputs
5. Append any new `## Action Items` entries with `- [ ]` checkboxes

### Conflict Handling
- If the section already exists, **append**, never overwrite
- Preserve all existing content above and below the insertion point

---

## Step 3 — Update Project Note

**File path pattern**: `{vault}/Projects/{ProjectName}.md`

### Project Note Structure (create if missing)

```markdown
---
tags: [project, {tech-tags}]
status: active | paused | completed
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
---

# {ProjectName}

## Overview
{one paragraph project description}

## Tech Stack
{see Step 4 output}

## Session Log
{chronological session entries — newest first}

## Problems & Solutions
{see Step 5 output}

## Related Projects
{see Step 7 output}

## Knowledge Nodes
{see Step 8 output}
```

### Session Log Entry Format

```markdown
### {YYYY-MM-DD} · {Session Topic}
> [[Daily/{YYYY-MM-DD}]] · {duration}

{summary paragraph}

**Changes**:
- {change 1}
- {change 2}

**Open Issues**: {or "none"}
```

Insert at the **top** of `## Session Log` (newest-first order).

---

## Step 4 — Extract Tech Stack

Parse the session for all mentioned technologies. For each tech found:

### Detection Rules
- Programming languages: Python, TypeScript, Swift, Rust, Go …
- Frameworks/libraries: FastAPI, React, PyQt5, SwiftUI, OpenCV …
- Tools & CLIs: Docker, Git, npm, pip, Homebrew …
- APIs/services: OpenAI, Anthropic, DeepSeek, WeChat …
- Concepts: REST, IPC, PTY, MediaPipe …

### Output Format (for Project Note `## Tech Stack`)

```markdown
## Tech Stack

| Category | Technologies |
|----------|-------------|
| Language | Python · TypeScript |
| Framework | FastAPI · PyQt5 |
| Tool | Docker · Git |
| API | Anthropic · DeepSeek |
| Concept | IPC · PTY |
```

### Global Index Update

Also update `{vault}/Meta/Tech Stack Index.md`:

```markdown
## {TechName}
- Used in: [[ProjectA]], [[ProjectB]]
- Last seen: {YYYY-MM-DD}
- Notes: {any version or usage notes}
```

Merge with existing entries — never duplicate.

---

## Step 5 — Extract Problems & Solutions

Scan the session for question/answer, problem/fix, error/resolution pairs.

### Detection Signals
- Phrases: "报错", "error", "issue", "fix", "solution", "how to", "为什么", "怎么", "solved by"
- Code snippets preceded by an error, followed by a working version
- User expressing frustration → Claude providing a resolution

### Q&A Entry Format

```markdown
### {Short problem title}
**Date**: {YYYY-MM-DD}
**Project**: [[{ProjectName}]]
**Context**: {1-2 sentences of context}

**Problem**:
{description}

**Solution**:
{description or code block}

**Tags**: #{tag1} #{tag2}
```

### Storage Locations
1. **In Project Note** under `## Problems & Solutions`
2. **In Q&A Archive** at `{vault}/Meta/QA Archive.md` — append in reverse-chronological order

---

## Step 6 — Auto-create Wiki Links

Scan all generated text for proper nouns, tech names, and project references. Replace bare mentions with `[[WikiLinks]]`.

### Linking Rules

| Condition | Action |
|-----------|--------|
| Mentions a known project | `[[Projects/ProjectName]]` |
| Mentions a tech in Tech Stack Index | `[[Tech/TechName]]` or inline tag |
| Mentions a date | `[[Daily/YYYY-MM-DD]]` |
| Mentions a person / team | `[[People/Name]]` if note exists |
| First occurrence only | Link it; subsequent mentions = plain text |

### Link Validation
Before writing, check if target note exists in vault:
- **Exists** → standard `[[link]]`
- **Doesn't exist** → create a stub note at the target path with frontmatter only, then link

Stub template:
```markdown
---
tags: [stub]
created: {YYYY-MM-DD}
---
# {Title}
> [!note] Stub — to be filled in
```

---

## Step 7 — Auto-establish Project Associations

After processing session content, infer relationships between projects.

### Association Types

```
[[ProjectA]] --uses--> [[LibraryX]]
[[ProjectA]] --inspired-by--> [[ProjectB]]
[[ProjectA]] --shares-stack-with--> [[ProjectC]]
[[ProjectA]] --evolved-from--> [[ProjectD]]
```

### Detection Logic
1. Same tech stack overlap ≥ 2 items → `shares-stack-with`
2. Current project was mentioned as building on a previous one → `evolved-from`
3. A library/tool first used in ProjectA now appears in ProjectB → `uses` (for the lib)
4. User explicitly says "similar to" or "like X" → `inspired-by`

### Output Location: `## Related Projects` in Project Note

```markdown
## Related Projects

- [[AgentWatch]] — `shares-stack-with` (Swift, SwiftUI)
- [[wxbot]] — `evolved-from` (Node.js + FastAPI architecture)
- [[PPT Generator]] — `shares-stack-with` (FastAPI, DeepSeek API)
```

---

## Step 8 — Maintain Knowledge Graph

Write machine-readable graph edges to `{vault}/Meta/Knowledge Graph.md`.

### Edge Format (Dataview-compatible)

```markdown
## Edges

| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|
| [[PyQt5]] | used-in | [[FingerCounter]] | 2025-06-01 | [[Daily/2025-06-01]] |
| [[OpenCV]] | used-in | [[FingerCounter]] | 2025-06-01 | [[Daily/2025-06-01]] |
| [[FingerCounter]] | evolved-from | [[AgentWatch]] | 2025-06-01 | [[Daily/2025-06-01]] |
```

Append new edges; never delete existing ones. Deduplicate by `(Source, Relation, Target)` key.

### Node Registry

Also maintain `{vault}/Meta/Nodes.md`:

```markdown
| Node | Type | First Seen | Projects |
|------|------|-----------|---------|
| [[PyQt5]] | framework | 2025-05-10 | [[FingerCounter]], [[DormManager]] |
```

---

## Output Checklist

Before finishing, confirm:

- [ ] Session Summary produced
- [ ] Daily Note updated (section appended, not overwritten)
- [ ] Project Note updated (session log entry at top)
- [ ] Tech Stack table updated in Project Note + Index
- [ ] Q&A pairs extracted and stored in both Project Note and Archive
- [ ] All proper nouns wiki-linked; stubs created for missing targets
- [ ] Project associations inferred and written
- [ ] Knowledge Graph edges appended; Nodes registry updated

---

## File Output Format

When Claude cannot directly write to the vault, output **one fenced block per file**, labeled with its vault path:

````
```obsidian-file
path: Daily/2025-06-03.md
action: append | create | replace-section
section: ## AI Sessions
---
{file content here}
```
````

The user can then paste or use a sync script. See `scripts/sync.py` for automated vault writing.

---

## References

- `references/templates.md` — Full Markdown templates for Daily Note, Project Note, Tech Index, Q&A Archive, Knowledge Graph
- `scripts/sync.py` — Python script to write output blocks directly to a local Obsidian vault
- `scripts/parse_session.py` — Helpers for extracting tech/QA/links from raw conversation text

Read these when you need the full template content or want to run automated sync.