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
interlinked notes into the user's Obsidian vault. Updates Daily Notes, Project Notes,
Tech Index, QA Archive, and Knowledge Graph — all append-only, never destructive.

## Mode Router

Check whether this is the first run:

```
config/vault_config.json exists? ──No──> SETUP MODE ──> Run scripts/setup.py, then exit
    │
   Yes
    │
    v
SYNC MODE ──> extract.py → write_vault.py → graph_update.py
```

## SETUP MODE (first run)

Run the setup wizard:

```bash
python scripts/setup.py
```

This script will:
1. Search for Obsidian vaults on this system
2. Ask the user to select or enter a vault path
3. Validate the vault is usable
4. Ask for preferences (language, auto-linking, graph)
5. Write `config/vault_config.json`
6. Bootstrap vault directory structure (`Daily/`, `Projects/`, `Meta/`)

If `scripts/setup.py` fails or the user needs a manual path, fall back to `AskUserQuestion`.

## SYNC MODE (every task end)

### Quick Reference

| Task | Where to go |
|------|-------------|
| Read vault config | `config/vault_config.json` |
| Extract knowledge from session | Run `python scripts/extract.py` |
| Write notes into vault | Run `python scripts/write_vault.py` |
| Update knowledge graph | Run `python scripts/graph_update.py` |
| How to classify tech / detect changes | Read `references/extract_rules.md` |
| Note format templates | Read `references/note_templates.md` |
| Graph node/edge type definitions | Read `references/graph_schema.md` |
| Recommended vault directory layout | Read `references/vault_structure.md` |
| Complex session → delegate to sub-agent | Read `agents/knowledge_extractor.md` |

### Core Pipeline

```bash
# Step 1: Extract structured knowledge from the conversation
python scripts/extract.py --session-text "<conversation>" --output /tmp/extracted.json

# Step 2: Write notes into the vault (Daily, Project, Tech Index, QA Archive)
python scripts/write_vault.py --input /tmp/extracted.json

# Step 3: Update knowledge graph edges and node registry
python scripts/graph_update.py --input /tmp/extracted.json
```

### Step-by-step with AI oversight

Scripts handle deterministic operations (JSON parsing, file I/O, dedup).
The AI handles semantic judgments (project name inference, tech classification, relation inference).

**Step 1 — Extract**

`scripts/extract.py` parses the conversation and outputs a JSON object. Review the output
and refine as needed before passing to Step 2. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `session_topic` | string | One-line session summary |
| `project_name` | string | Inferred project name, or "通用" |
| `summary` | string | ≤3 sentence summary, past tense |
| `tech_stack` | object | `{category: [tech_names]}` |
| `changes` | string[] | What was built/fixed/changed |
| `problems_solved` | object[] | `[{title, context, problem, solution, tags}]` |
| `open_issues` | string[] | Unresolved items |
| `next_actions` | string[] | Action items with owners if known |
| `timestamp` | string | ISO 8601 |

If the session is complex (multi-project, large codebase), spawn the sub-agent defined in
`agents/knowledge_extractor.md` to produce the extraction JSON.

**Step 2 — Write**

`scripts/write_vault.py` writes to the vault. What it does:

| Target | File | Operation |
|--------|------|-----------|
| Daily Note | `<vault>/Daily/YYYY-MM-DD.md` | Append to `## AI Sessions` |
| Project Note | `<vault>/Projects/{name}.md` | Prepend to `## Session Log`; update `## Tech Stack` table |
| Tech Index | `<vault>/Meta/Tech Stack Index.md` | Merge entries, never duplicate |
| QA Archive | `<vault>/Meta/QA Archive.md` | Append problem-solution entries |

**Step 3 — Graph**

`scripts/graph_update.py` maintains the knowledge graph:

| File | Operation |
|------|-----------|
| `<vault>/Meta/Knowledge Graph.md` | Append edges, dedup by `(Source, Relation, Target)` |
| `<vault>/Meta/Nodes.md` | Merge node registry, update project lists |

Also infers cross-project relations (`shares-stack-with`, `evolved-from`) by scanning
existing project notes — see `references/graph_schema.md` for detection rules.

### Output Checklist

After pipeline completes, verify:

- [ ] Daily Note updated (append only)
- [ ] Project Note updated (session log + tech stack + frontmatter `updated:`)
- [ ] Tech Stack Index merged (no duplicates)
- [ ] QA Archive appended (if problems solved)
- [ ] Knowledge Graph edges appended (deduped)
- [ ] Nodes registry updated
- [ ] Cross-project associations inferred and written

## Auto-Trigger Heuristics

Fire this skill when an agent session has produced substantive work. Signals:

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
