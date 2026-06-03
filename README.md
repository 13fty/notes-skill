# Obsidian Second Brain

Sync AI agent conversation sessions into an [Obsidian](https://obsidian.md) vault — structured notes, knowledge graphs, and cross-referenced insights.

Works with Claude Code, Gemini CLI, Codex, Cursor, and other AI agents.

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd obsidian-second-brain

# 2. Initialize — auto-discovers your vault
python scripts/cli.py init

# 3. Run a diagnostic
python scripts/cli.py doctor

# 4. Sync AI output to vault
cat session_output.md | python scripts/cli.py sync --project my-project
```

## Commands

| Command | What it does |
|---------|-------------|
| `init` | First-time wizard: search → select → validate → save config |
| `config list` | Show current configuration |
| `config set <key> <value>` | Change a preference |
| `validate` | Check vault health |
| `search` | Find all Obsidian vaults on this system |
| `repair` | Recover when vault path breaks |
| `sync` | Write AI output blocks into vault |
| `migrate` | Upgrade config format version |
| `doctor` | Full diagnostic report |

## Configuration

Config and state are stored at `~/.obsidian-skill/`:

- `config.json` — vault path, preferences, agent type
- `state.json` — sync history, discovered vaults, statistics

This path is agent-agnostic — all AI agents share the same config.

## Skill Integration

### Claude Code

Register `skill.md` as a custom skill. The skill auto-detects configuration on first run — it will run `python scripts/cli.py search` to find your vault, or ask you for the path.

### Gemini CLI / Codex / Other Agents

Point your agent's instruction file to `skill.md` and ensure `python scripts/cli.py` is on the PATH or referenced by absolute path.

## Directory

```
obsidian-second-brain/
├── skill.md              # Core skill instructions (agent-agnostic)
├── scripts/
│   └── cli.py            # Unified CLI (8 subcommands)
├── lib/
│   ├── config.py         # Config + state management
│   ├── vault.py          # Vault search, validate, repair
│   ├── sync.py           # Block parser + vault writer
│   ├── parser.py         # Tech stack, Q&A, wiki link extraction
│   └── templates.py      # Template loading + rendering
├── templates/
│   ├── daily.md
│   ├── project.md
│   └── knowledge.md
└── .gitignore
```

## Requirements

- Python 3.11+
- No external dependencies (stdlib only)

## License

MIT
