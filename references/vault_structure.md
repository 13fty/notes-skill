# Vault Directory Structure

Recommended Obsidian vault layout for the agent-knowledge system. The setup script (`scripts/setup.py`) bootstraps this structure on first run.

## Table of Contents

- [Directory Tree](#directory-tree)
- [Directory Purposes](#directory-purposes)
- [File Naming Conventions](#file-naming-conventions)
- [What Gets Written Where](#what-gets-written-where)

---

## Directory Tree

```
MyVault/                          ← Vault root (user's existing vault)
│
├── Daily/                        ← Daily notes, one file per day
│   ├── 2026-06-03.md
│   └── 2026-06-04.md
│
├── Sessions/                     ← Session logs (one per agent task)
│   ├── 2026-06-04-agent-knowledge-v2.md
│   └── ...
│
├── Projects/                     ← Project notes, one file per project
│   ├── MyAPI.md
│   ├── WeatherTracker.md
│   └── ...
│
├── Snippets/                     ← Reusable code snippets
│   ├── pty-nonblock-write.md
│   ├── docker-prune-cleanup.md
│   └── ...
│
├── Concepts/                     ← Zettelkasten atomic concept notes
│   ├── IPC.md
│   ├── RAG.md
│   └── ...
│
├── Tech/                         ← Technology cards (one per tool/framework)
│   ├── FastAPI.md
│   ├── Docker.md
│   └── ...
│
├── Decisions/                    ← Architecture Decision Records
│   ├── ADR-001-use-opencv-over-mediapipe.md
│   ├── ADR-002-append-only-vault-writes.md
│   └── ...
│
├── Meta/                         ← Global indices and knowledge graph
│   ├── Tech Stack Index.md       ← Per-tech cross-project index
│   ├── QA Archive.md             ← All problem-solution pairs
│   ├── Knowledge Graph.md        ← Edge table (Dataview-compatible)
│   └── Nodes.md                  ← Node registry
│
└── (existing user content)       ← Never modified by noteskill
```

---

## Directory Purposes

### `Daily/`

- One file per day: `YYYY-MM-DD.md`
- Created on first session of the day
- Stores **lightweight session callouts** (3-5 lines each) under `## AI Sessions`
- Full session detail lives in `Sessions/` — Daily only has a summary + `[[Sessions/...]]` link
- Agent may update `## Action Items` with next steps
- Agent may check off `## Today's Progress` items
- **Never overwrites** user's manual content outside designated sections

### `Sessions/`

- One file per agent task session: `YYYY-MM-DD-{topic-slug}.md`
- Created at the end of every substantive agent task
- Contains the **complete session detail**: changes made, key decisions, problems solved, tech used, open issues
- Cross-links to Project Note and Daily Note
- **Append-only** — wrong turns and dead ends are preserved as process history
- **This is the canonical source** for session content. Daily/ callouts are summaries that link here.

### `Projects/`

- One file per project: `{ProjectName}.md`
- Created automatically when a new project is detected
- Session logs are **prepended** (newest first)
- Tech Stack table is **merged** (new techs appended to category rows)
- Q&A entries appended to `## Problems & Solutions`
- Cross-project relations written to `## Related Projects`
- Frontmatter `updated:` field reflects most recent sync date

### `Meta/`

Global indices — these are the "knowledge graph" files:

| File | Contents | Update Rule |
|------|----------|-------------|
| `Tech Stack Index.md` | Per-tech sections listing projects that use it | Merge (update date, add project) |
| `QA Archive.md` | All problem-solution pairs across all projects | Prepend (newest first), dedup by title |
| `Knowledge Graph.md` | Edge table: Source → Relation → Target | Append edges, dedup by triple |
| `Nodes.md` | Node registry: name, type, first seen, projects | Merge (add project, keep earliest date) |

### `Snippets/`

- One file per reusable code snippet: `{descriptive-slug}.md`
- Each snippet covers exactly ONE specific usage of a tool or technique
- Gradually builds into your personal Stack Overflow
- Dedup by title before creating — merge if a snippet on the same topic exists

### `Concepts/`

- Zettelkasten atomic concept notes: one idea, one note
- Each note expresses a concept in your own words (the "我的理解" section)
- Heavily interlinked to related concepts, projects, and snippets
- Split compound topics — if a note covers two distinct ideas, split it

### `Tech/`

- One file per technology (framework, library, tool): `{TechName}.md`
- Aggregates all knowledge about that tech: core usage, pitfalls, version history
- Stub card created automatically on first use
- Updated on reuse — new pitfalls appended, `last_used` refreshed
- Status lifecycle: `learning` → `active` → `deprecated`

### `Decisions/`

- Architecture Decision Records: `ADR-{###}-{slug}.md`
- Numbered sequentially — scan existing ADRs for the highest number
- Captures *why* a choice was made, not just what was chosen
- Must include ≥2 considered alternatives
- When reversed, don't edit — create a new ADR that supersedes the old one

---

## File Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Daily Note | `YYYY-MM-DD.md` | `2026-06-04.md` |
| Session Log | `YYYY-MM-DD-{topic-slug}.md` | `2026-06-04-fastapi-deploy-debug.md` |
| Project Note | `{ProjectName}.md` (PascalCase or kebab-case) | `MyAPI.md`, `weather-tracker.md` |
| Snippet | `{tool}-{action}.md` (kebab-case) | `pty-nonblock-write.md` |
| Concept Note | `{ConceptName}.md` (PascalCase) | `IPC.md`, `RAG.md` |
| Tech Card | `{TechName}.md` (canonical casing) | `FastAPI.md`, `TypeScript.md` |
| ADR | `ADR-{###}-{slug}.md` | `ADR-003-use-opencv-over-mediapipe.md` |
| Meta files | `{Descriptive Name}.md` (Title Case) | `Tech Stack Index.md` |

---

## What Gets Written Where

For a session about project `MyAPI` involving Python, FastAPI, Docker:

```
Session ──────────────────────────────────────────────────
│
├── Sessions/2026-06-04-{topic}.md    ← full session log (changes, decisions, tech)
│
├── Daily/2026-06-04.md               ← append callout to ## AI Sessions
│
├── Projects/MyAPI.md                 ← prepend to ## Session Log
│                                    ← merge into ## Tech Stack table
│                                    ← append to ## Problems & Solutions
│                                    ← write ## Related Projects
│
├── Snippets/{name}.md                ← create if code block ≥5 lines detected
│
├── Concepts/{Name}.md                ← create if new concept explained
│
├── Tech/{Name}.md                    ← create stub on first use, update on reuse
│
├── Decisions/ADR-###-{slug}.md       ← create if architecture decision detected
│
├── Meta/Tech Stack Index.md          ← merge entry for each tech
│
├── Meta/QA Archive.md                ← append problem-solution pairs
│
├── Meta/Knowledge Graph.md           ← append used-in edges
│
└── Meta/Nodes.md                     ← merge node entries
```

---

## Safety Constraints

1. **Append-only**: Never delete or overwrite existing content outside of designated merge sections
2. **Merge sections**: Tech Stack table, Tech Stack Index, Nodes registry — these are the only places where existing content is modified (to add or update)
3. **User territory**: Content outside `## AI Sessions`, `## Session Log`, `## Problems & Solutions`, `## Related Projects`, and `## Tech Stack` is user territory — never modify
4. **Backup consideration**: For large vaults, the write script (`write_vault.py`) reads the full file into memory. This is safe for vaults under 10MB. For larger vaults, consider incremental approaches
