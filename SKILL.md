---
name: obsidian
description: >
  Process AI agent conversation sessions and sync structured knowledge into an Obsidian vault.
  Trigger on: "save to obsidian", "update my notes", "log this session", "记录一下", "整理笔记",
  "add to daily note", "extract tech stack", "create wiki links", "update project note",
  or any request to persist conversation content into an Obsidian vault.
---

# Obsidian Knowledge Sync Skill

Read the current conversation and write structured, interlinked notes into the user's Obsidian vault.

## Before You Start

The vault path is stored in `~/.obsidian-skill/config.json`:

```json
{"vault_path": "/absolute/path/to/vault"}
```

**If config doesn't exist** or vault is unreachable, follow Step 0 in `docs/workflow.md`.

## What To Do

Follow the 8 steps in `docs/workflow.md`. In order:

1. Summarize the session
2. Update the Daily Note
3. Update the Project Note
4. Extract the tech stack
5. Extract Q&A pairs
6. Generate Wiki Links
7. Infer project associations
8. Maintain the knowledge graph

## Where To Find Everything

| Need | File |
|------|------|
| Step-by-step instructions | `docs/workflow.md` |
| Real examples of output | `docs/examples.md` |
| Edge cases & troubleshooting | `docs/faq.md` |
| Tech classification tables | `assets/references.md` |
| Daily Note template | `templates/output.md` |
| Project Note template | `templates/report.md` |
| Knowledge Graph template | `templates/knowledge.md` |

## Helper Scripts

Two Python scripts handle things AI cannot do (filesystem scanning, path validation):

```bash
# Find all Obsidian vaults on this system
python scripts/helper.py --json

# Validate a vault path
python scripts/validator.py --path /path/to/vault
```

## Output Checklist

After all 8 steps, confirm:

- [ ] Daily Note updated (append only, never overwrite)
- [ ] Project Note updated (session log at top)
- [ ] Tech Stack table updated (Project Note + Meta Index)
- [ ] Q&A pairs extracted (Project Note + QA Archive)
- [ ] Wiki Links applied; stubs created for missing targets
- [ ] Project associations written
- [ ] Knowledge Graph edges appended; Nodes registry updated
