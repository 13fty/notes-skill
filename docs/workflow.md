# Detailed Workflow

Eight steps to process a conversation session into Obsidian notes.

---

## Step 0 — Ensure Vault Access

### 0.1 Check config

Read `~/.obsidian-skill/config.json`. If it exists and contains a `vault_path`, go to 0.2.

### 0.2 Validate the vault

```bash
python scripts/validator.py --path "<vault_path>"
```

Parse the JSON output:
- `valid: true` → vault ready. Store path as `VAULT`. Continue to Step 1.
- `valid: false` → vault broken. Go to 0.3.

### 0.3 First-time setup (or repair)

```bash
python scripts/helper.py --json
```

**If vaults found:**
Use `AskUserQuestion` to present the list. Write chosen path:
```bash
mkdir -p ~/.obsidian-skill
echo '{"vault_path": "<chosen_path>"}' > ~/.obsidian-skill/config.json
```
Store as `VAULT`. Continue to Step 1.

**If no vaults found:**
Use `AskUserQuestion`: "No Obsidian vaults found. Please enter the full path to your Obsidian vault (e.g. `/Users/name/Documents/Obsidian`):"
Validate: `python scripts/validator.py --path "<user_path>"`
If valid, write config. If invalid, ask again.

**Fallback** (AskUserQuestion unavailable): Ask in plain text, wait for reply, validate manually.

---

## Step 1 — Summarize Session

Read the current conversation. Produce a summary:

| Field | Instruction |
|-------|------------|
| **主题** | One-line topic |
| **项目** | Project name inferred from context, or "通用" |
| **核心产出** | Bullet list, max 5 items |
| **未解决问题** | Bullet list of open issues, or "无" |
| **下一步行动** | Bullet list, with owner/deadline if mentioned |

Rules: ≤20 lines, past tense, no code blocks in the summary.

---

## Step 2 — Update Daily Note

File: `<VAULT>/Daily/YYYY-MM-DD.md`

1. Read the existing Daily Note. If missing, create from `templates/output.md`.
2. Find or create `## AI Sessions`.
3. Append a callout block:

```markdown
> [!summary]- HH:mm · {Session Topic} · [[{ProjectName}]]
> {Summary paragraph from Step 1}
> **Tech**: {comma-separated tech tags from Step 4}
> **Tags**: #{tag1} #{tag2}
```

4. Check off matching items in `## Today's Progress`.
5. Append new items under `## Action Items` as `- [ ]`.

Always append, never overwrite existing content.

---

## Step 3 — Update Project Note

File: `<VAULT>/Projects/{ProjectName}.md`

1. Read the existing Project Note. If missing, create from `templates/report.md`. Replace `{{project}}` with project name.
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

3. Update frontmatter `updated:` to today.

---

## Step 4 — Extract Tech Stack

Scan the conversation for technologies. Classification table is in `assets/references.md`.

Update Project Note `## Tech Stack`:

```markdown
| Category | Technologies |
|----------|-------------|
| Language | Python · TypeScript |
| Framework | FastAPI · PyQt5 |
| Tool | Docker · Git |
| API | Anthropic · DeepSeek |
| Concept | IPC · PTY |
```

Update `<VAULT>/Meta/Tech Stack Index.md` — merge, never duplicate:

```markdown
## {TechName}
- Used in: [[Projects/{ProjectName}]]
- Last seen: YYYY-MM-DD
```

---

## Step 5 — Extract Q&A / Problem-Solution Pairs

Scan for patterns: errors, "报错", "怎么", "why does", "not working" → fixes, "solved by", "解决了".

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

**In `<VAULT>/Meta/QA Archive.md`:** Append same entry, newest first.

---

## Step 6 — Generate Wiki Links

| Condition | Link format | Rule |
|-----------|------------|------|
| Date mention | `[[Daily/YYYY-MM-DD]]` | first occurrence only |
| Known project name | `[[Projects/Name]]` | first occurrence only |
| Tech in Tech Stack Index | `[[Tech/Name]]` or inline tag | first occurrence only |

Create stub for missing targets:

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

| Signal | Relation |
|--------|----------|
| ≥2 overlapping tech stack items with another project | `shares-stack-with` |
| User says "based on X", "building on X" | `evolved-from` |
| User says "similar to X", "like X" | `inspired-by` |
| A library appears in both projects | `uses` |

**Output — Project Note `## Related Projects`:**

```markdown
- [[OtherProject]] — `shares-stack-with` (Python, FastAPI)
- [[OldProject]] — `evolved-from`
```

---

## Step 8 — Maintain Knowledge Graph

Append edges to `<VAULT>/Meta/Knowledge Graph.md`:

```markdown
| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|
| [[PyQt5]] | used-in | [[FingerCounter]] | YYYY-MM-DD | [[Daily/YYYY-MM-DD]] |
```

Deduplicate by `(Source, Relation, Target)`. Never delete existing edges.

Update `<VAULT>/Meta/Nodes.md`:

```markdown
| Node | Type | First Seen | Projects |
|------|------|-----------|---------|
| [[PyQt5]] | framework | YYYY-MM-DD | [[FingerCounter]], [[DormManager]] |
```
