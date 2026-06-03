---
name: obsidian
description: >
  Process AI agent conversation sessions and sync structured knowledge into an Obsidian vault.
  Trigger on: "save to obsidian", "update my notes", "log this session", "记录一下", "整理笔记",
  "add to daily note", "extract tech stack", "create wiki links", "update project note",
  or any request to persist conversation content into an Obsidian vault.
  Works with Claude Code, Gemini CLI, Codex, Cursor, and other AI agents.
---

# Obsidian Knowledge Sync Skill

Process the current conversation session and write structured, interlinked Markdown notes
into the user's Obsidian vault. Eight steps — execute them in order.

---

## Step 0 — Ensure Vault Access

The vault path is stored in `~/.obsidian-skill/config.json`. This file is a simple JSON:

```json
{"vault_path": "/absolute/path/to/vault"}
```

### 0.1 Check config exists

Read `~/.obsidian-skill/config.json`. If it exists and contains a `vault_path`, go to 0.2.

### 0.2 Validate the vault

Run: `python scripts/validate_vault.py --path "<vault_path>"`. Parse the JSON output.

- `valid: true` → vault is ready. Store `<vault_path>` in memory as `VAULT`. Continue to Step 1.
- `valid: false` → vault is broken. Go to 0.3.

### 0.3 First-time setup (or repair)

Run: `python scripts/search_vault.py --json`. Parse the JSON array.

**If vaults found:**
Use `AskUserQuestion` to present them. Let the user pick one.
Write the chosen path to `~/.obsidian-skill/config.json`:
```bash
mkdir -p ~/.obsidian-skill
echo '{"vault_path": "<chosen_path>"}' > ~/.obsidian-skill/config.json
```
Store as `VAULT`. Continue to Step 1.

**If no vaults found:**
Use `AskUserQuestion` to ask: "No Obsidian vaults found. Please enter the full path to your Obsidian vault (e.g. `/Users/name/Documents/Obsidian`):"
Validate with `python scripts/validate_vault.py --path "<user_path>"`.
If valid, write config as above. If invalid, ask again.

**Fallback** (AskUserQuestion unavailable): Ask in plain text, wait for reply, validate manually.

---

## Step 1 — Summarize Session

Read the current conversation. Extract:

| Field | Instruction |
|-------|------------|
| **主题** | One-line topic in the user's preferred language |
| **项目** | Project name inferred from context, or "通用" |
| **核心产出** | Bullet list, max 5 items of what was accomplished |
| **未解决问题** | Bullet list of open issues, or "无" |
| **下一步行动** | Bullet list of next steps, with owner/deadline if mentioned |

Keep the summary ≤20 lines. Use past tense. No code blocks in the summary.

---

## Step 2 — Update Daily Note

File: `<VAULT>/Daily/YYYY-MM-DD.md`

1. **Read** the Daily Note if it exists. If not, create from `templates/daily.md`.
2. Find or create the `## AI Sessions` section.
3. **Append** a callout block below the section header:

```markdown
> [!summary]- HH:mm · {Session Topic} · [[{ProjectName}]]
> {Summary paragraph from Step 1}
> **Tech**: {comma-separated tech tags from Step 4}
> **Tags**: #{tag1} #{tag2}
```

4. If the `## Today's Progress` section has checkboxes matching session outputs, check them off.
5. Append any new action items under `## Action Items` as `- [ ]`.

**Rule:** Always append, never overwrite existing content above or below the insertion point.

---

## Step 3 — Update Project Note

File: `<VAULT>/Projects/{ProjectName}.md`

1. **Read** the Project Note if it exists. If not, create from `templates/project.md`.
   Replace `{{project}}` with the project name.
2. Under `## Session Log`, **prepend** (newest first):

```markdown
### YYYY-MM-DD · {Session Topic}
> [[Daily/YYYY-MM-DD]] · ~{duration}

{summary paragraph}

**Changes**:
- {change 1}
- {change 2}

**Open Issues**: {or "none"}
```

3. Update the frontmatter `updated:` field to today's date.

---

## Step 4 — Extract Tech Stack

Scan the conversation for technologies mentioned. Use this classification:

| Category | Look for |
|----------|---------|
| Language | Python, TypeScript, JavaScript, Swift, Rust, Go, Kotlin, Java, C++, C#, Ruby, PHP, Bash, Shell |
| Framework | FastAPI, Flask, Django, React, Vue, Next.js, Nuxt, PyQt5, PyQt6, SwiftUI, UIKit, Express, NestJS, Spring, Rails, Laravel |
| Tool | Docker, Git, npm, pip, Homebrew, Make, Webpack, Vite, Pytest, Jest, GitHub Actions, Nginx, Caddy |
| API/Service | Anthropic, OpenAI, DeepSeek, Gemini, Claude, WeChat, Telegram, Slack, AWS, GCP, Azure, Vercel, Railway |
| Library | OpenCV, MediaPipe, NumPy, Pandas, Matplotlib, SQLAlchemy, Pydantic, Uvicorn, aiohttp, requests, Tailwind, shadcn |
| Concept | REST, GraphQL, WebSocket, gRPC, IPC, PTY, MVC, MVVM, microservices, RAG, embeddings, LLM, AI agent |

**Output — Update Project Note `## Tech Stack`:**

```markdown
| Category | Technologies |
|----------|-------------|
| Language | Python · TypeScript |
| Framework | FastAPI · PyQt5 |
| Tool | Docker · Git |
| API | Anthropic · DeepSeek |
| Concept | IPC · PTY |
```

**Output — Update `<VAULT>/Meta/Tech Stack Index.md`:**

For each tech found, add or update an entry. Merge with existing entries — never duplicate.

```markdown
## {TechName}
- Used in: [[Projects/{ProjectName}]]
- Last seen: YYYY-MM-DD
```

---

## Step 5 — Extract Q&A / Problem-Solution Pairs

Scan for patterns: errors, "报错", "怎么", "why does", "not working", followed by fixes, "solved by", "解决了", "成功了".

For each pair found:

**In Project Note `## Problems & Solutions`:**

```markdown
### {Short problem title}
**Date**: YYYY-MM-DD
**Context**: {1-2 sentences}

**Problem**:
{description}

**Solution**:
{description or code block}

**Tags**: #tag1 #tag2
```

**In `<VAULT>/Meta/QA Archive.md`:**
Append the same entry in reverse-chronological order.

---

## Step 6 — Generate Wiki Links

Scan all generated text and apply `[[WikiLinks]]`:

| Condition | Link format | Rule |
|-----------|------------|------|
| Date mention | `[[Daily/YYYY-MM-DD]]` | first occurrence only |
| Known project name | `[[Projects/Name]]` | first occurrence only |
| Tech in Tech Stack Index | `[[Tech/Name]]` or inline tag | first occurrence only |

If a link target doesn't exist as a note, create a minimal stub:

```markdown
---
tags: [stub]
created: YYYY-MM-DD
---
# {Title}
> [!note] Stub — to be filled in
```

---

## Step 7 — Infer Project Associations

Check relationships between the current project and others in the vault:

| Signal | Relation |
|--------|----------|
| ≥2 overlapping tech stack items with another project | `shares-stack-with` |
| User says "based on X", "building on X" | `evolved-from` |
| User says "similar to X", "like X" | `inspired-by` |
| A library appears in both projects | `uses` (for the library) |

**Output — In Project Note `## Related Projects`:**

```markdown
- [[OtherProject]] — `shares-stack-with` (Python, FastAPI)
- [[OldProject]] — `evolved-from`
```

---

## Step 8 — Maintain Knowledge Graph

Append edges to `<VAULT>/Meta/Knowledge Graph.md` (Dataview-compatible format):

```markdown
| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|
| [[PyQt5]] | used-in | [[FingerCounter]] | YYYY-MM-DD | [[Daily/YYYY-MM-DD]] |
| [[FingerCounter]] | evolved-from | [[AgentWatch]] | YYYY-MM-DD | [[Daily/YYYY-MM-DD]] |
```

Deduplicate by `(Source, Relation, Target)`. Never delete existing edges.

Also update `<VAULT>/Meta/Nodes.md`:

```markdown
| Node | Type | First Seen | Projects |
|------|------|-----------|---------|
| [[PyQt5]] | framework | YYYY-MM-DD | [[FingerCounter]], [[DormManager]] |
```

---

## Output Checklist

Before finishing, confirm all steps:

- [ ] Step 0: Vault accessible, `VAULT` path stored
- [ ] Step 1: Session summary produced (topic, project, outcomes, next steps)
- [ ] Step 2: Daily Note updated (appended, not overwritten)
- [ ] Step 3: Project Note updated (session log entry at top)
- [ ] Step 4: Tech Stack table updated (Project Note + Meta Index)
- [ ] Step 5: Q&A pairs extracted (Project Note + QA Archive)
- [ ] Step 6: Wiki links applied to all proper nouns; stubs created for missing targets
- [ ] Step 7: Project associations inferred and written
- [ ] Step 8: Knowledge Graph edges appended; Nodes registry updated

---

## Templates

Full templates are in `templates/`:
- `templates/daily.md` — Daily Note structure
- `templates/project.md` — Project Note structure
- `templates/knowledge.md` — Knowledge Graph structure

Read them when creating a note for the first time.
