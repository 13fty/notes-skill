# Notes Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org/)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen.svg)](https://github.com)

An AI agent skill that auto-hooks into task completion and syncs structured knowledge into an [Obsidian](https://obsidian.md) vault. Unlike manual-trigger note-taking, this system fires automatically after substantive coding, debugging, or design sessions — extracting what was learned and persisting it without the user having to ask.

## Design Philosophy

- **Auto-hook**: Fires after agent tasks complete, not only on explicit user request
- **3-layer note framework**: Session → Project → Knowledge — clear information flow from raw conversations to reusable knowledge
- **8-step AI-driven pipeline**: Summary → Daily → Project → Knowledge Nodes → Q&A → Wiki Links → Relations → Graph
- **Append-only**: Never deletes or overwrites user content; all writes are appends or section-level merges
- **Unified Knowledge nodes**: One template for all knowledge types (concept | tool | framework | pattern) — replacing separate Snippet, Concept Note, Tech Card, and ADR templates
- **Bilingual**: Chinese and English signal-word detection for tech classification, problem/solution pairing, and change tracking
- **Cross-project awareness**: Infers relationships between projects automatically (tech overlap, evolution chains)
- **Growth over time**: Knowledge graph accumulates edges; the longer you use it, the richer it gets

## Quick Start

### Prerequisites

- Python 3.9+ (stdlib only — no pip packages required)
- An [Obsidian](https://obsidian.md) vault with `.obsidian` directory
- Write access to the vault path

### Installation

1. **Clone or copy** this repository:

   ```bash
   git clone https://github.com/<your-username>/notes-skill.git
   ```

2. **Register the skill in Claude Code** (or your AI agent platform).

   > ⚠️ **Important:** Simply creating a symlink in `~/.claude/skills/` is NOT enough. Skills must be registered through Claude Code's plugin system. A bare symlink will show as "Unknown" and won't be callable.

   **Claude Code:**
   
   In Claude Code, run this slash command to install the skill:
   
   ```
   /plugin install /path/to/notes-skill
   ```
   
   This registers `notes-skill` in the plugin system and creates the proper symlink. Verify it worked by checking that the skill list shows `notes-skill` by name (not "Unknown").

   **Other platforms:** Register `SKILL.md` as a custom skill following your platform's documentation.

3. **First run** — the skill auto-detects it hasn't been set up and enters setup mode:

   ```bash
   python scripts/setup.py --discover    # Find Obsidian vaults on this system
   python scripts/setup.py --path ~/Documents/Obsidian  # Configure a specific vault
   ```

4. **Done.** After every substantial agent task, the skill automatically extracts knowledge and writes it to your vault.

## How It Works

### The 8-Step Pipeline

```
Session complete
      │
      ▼
Step 1: Generate session summary (AI-driven)
      │
      ├─ Step 2: Update Daily Note (append row to ## Sessions table)
      ├─ Step 3: Update Project Note (prepend to ## Changelog)
      ├─ Step 4: Extract tech → create/update Knowledge nodes ── parse_session.py
      ├─ Step 5: Extract Q&A → Session Log + Knowledge Node pitfalls ── parse_session.py
      ├─ Step 6: Auto-generate Wiki links (Daily/, Projects/, Knowledge/)
      ├─ Step 7: Infer cross-project relations (tech overlap ≥2)
      └─ Step 8: Maintain Knowledge-Graph + Projects-Index
      │
      ▼
sync.py writes obsidian-file blocks → Vault
```

### Two Script Utilities

| Script | Purpose |
|--------|---------|
| `parse_session.py` | NLP extraction: tech stack (6 categories), Q&A pairs (paragraph-based), Wiki link generation (first-occurrence-only, longest-match-first), session time (HHMM) |
| `sync.py` | Vault I/O: parses `obsidian-file` blocks or JSON, writes to Daily/Project/Knowledge/Knowledge-Graph/Projects-Index |

### Vault Layout (5 directories)

| Directory | Purpose | Example |
|-----------|---------|---------|
| `Sessions/` | One log per agent task | `2026-06-07-1430.md` |
| `Projects/` | One note per project (Changelog-based) | `MyApp.md` |
| `Daily/` | Daily overview (table-based Sessions list) | `2026-06-07.md` |
| `Knowledge/` | Unified knowledge nodes (concept\|tool\|framework\|pattern) | `Unix-Domain-Socket.md` |
| `Meta/` | Knowledge-Graph.md + Projects-Index.md | — |

### What Gets Written

| Target | File | Operation |
|--------|------|-----------|
| Daily Note | `Daily/YYYY-MM-DD.md` | Append row to `## Sessions` table (时间/项目/做了什么/时长) |
| Session Log | `Sessions/YYYY-MM-DD-HHMM.md` | Create full session detail (修改了什么/对话摘要/知识点/遗留问题/收获) |
| Project Note | `Projects/{name}.md` | Prepend to `## Changelog` (with file list + open issues) |
| Knowledge Node | `Knowledge/{Name}.md` | Create or merge (踩坑记录 table + 来源会话) |
| Knowledge Graph | `Meta/Knowledge-Graph.md` | Append edges (dedup by Source+Relation+Target) |
| Projects Index | `Meta/Projects-Index.md` | Merge project row (update date + tech) |

## Directory

```
notes-skill/
├── SKILL.md                       # ⭐ Entry point — AI reads this first (8-step + 3-layer guide)
├── LICENSE.txt                    # MIT License
├── README.md
├── README.zh-CN.md                # 中文说明
│
├── config/
│   └── vault_config.json          # Generated by setup.py (user-specific, not committed)
│
├── scripts/
│   ├── __init__.py                # Python package marker
│   ├── setup.py                   # First-time vault discovery & bootstrap
│   ├── parse_session.py           # Session → structured knowledge JSON
│   │                              #   Module A: Tech stack extraction
│   │                              #   Module B: Q&A pair extraction
│   │                              #   Module C: Wiki link generation
│   └── sync.py                    # Write knowledge to vault
│                                  #   Mode 1: obsidian-file blocks (design standard)
│                                  #   Mode 2: JSON pipeline (backward compat)
│
├── references/
│   └── templates.md               # All 6 note templates + tech classification rules
│                                  #   + graph schema + vault structure + naming conventions
│
├── obsidian-note-framework.md     # 3-layer note framework design doc
├── obsidian-skill-design.md       # 8-step skill architecture design doc
│
└── evals/
    └── evals.json                 # Regression test cases
```

## Usage

### obsidian-file block mode (recommended)

The AI generates `obsidian-file` blocks and pipes them to `sync.py`:

````bash
cat << 'EOF' | python scripts/sync.py
```obsidian-file
path: Sessions/2026-06-07-1430.md
action: create
---
---
date: 2026-06-07
time: 14:30
duration: 45min
project: MyAPI
type: coding
tags: [python, docker]

# 2026-06-07 14:30 · MyAPI · Fixed Docker build

## 📁 项目
[[Projects/MyAPI]] · `requirements.txt`, `Dockerfile`

## ✏️ 修改了什么
### 修改
- `requirements.txt` — Added pydantic dependency

## 💬 对话摘要
Fixed Docker build failure caused by missing pydantic.

## 🔗 涉及的知识点
| 知识点 | 关系 | 备注 |
|--------|------|------|
| [[Knowledge/Pydantic]] | 核心机制 | Build dependency |
```

```obsidian-file
path: Daily/2026-06-07.md
action: append
section: ## Sessions
---
| 14:30 | [[Projects/MyAPI]] | Fixed Docker build by adding pydantic | 45min |
```
EOF
````

**Three actions**: `create` (file doesn't exist), `append` (under a section heading), `replace-section` (entire section body).

### JSON pipeline mode (backward compatible)

```bash
# Step 1: Parse session text into structured JSON
python scripts/parse_session.py --session-text "<conversation>" --output /tmp/parsed.json

# Step 2: Write everything to the vault
python scripts/sync.py --input /tmp/parsed.json
```

### Dry run mode

```bash
python scripts/sync.py --input output.md --dry-run
python scripts/sync.py --input parsed.json --dry-run
```

Preview all changes before writing — safe to run anywhere.

## Auto-Trigger Heuristics

The skill fires automatically when a session has produced substantive work:

- ≥3 tool calls completed
- Code was written, edited, or debugged
- A bug was fixed or a feature was implemented
- New technologies or libraries were introduced
- User explicitly asked to record/save

It does **not** fire for single-question answers, conversational chat, or trivial file reads.

## Manual Triggers

You can also explicitly trigger it with phrases like:

- "记录一下" / "保存到 obsidian" / "更新笔记"
- "save this session" / "log this to obsidian"
- "整理到知识库" / "这次学到了什么"

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## License

MIT — see [LICENSE.txt](LICENSE.txt) for complete terms.
