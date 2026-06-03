# Obsidian Second Brain

An AI agent skill that processes conversation sessions and syncs structured knowledge into an [Obsidian](https://obsidian.md) vault.

Works with Claude Code, Gemini CLI, Codex, Cursor, and other AI agents.

## Quick Start

**For Claude Code users:** Register `skill.md` as a custom skill. The first time it runs, it will guide you through vault setup.

**Manual setup:**

```bash
# Find your vault
python scripts/search_vault.py --json

# Validate a vault
python scripts/validate_vault.py --path ~/Documents/Obsidian

# Set config manually (or let the AI do it for you)
mkdir -p ~/.obsidian-skill
echo '{"vault_path": "/path/to/your/vault"}' > ~/.obsidian-skill/config.json
```

## How It Works

The AI reads `skill.md` and executes 8 steps:

1. **Ensure Vault Access** — read config, auto-detect vaults, validate path
2. **Summarize Session** — extract topic, project, outcomes, next steps
3. **Update Daily Note** — append session summary to `Daily/YYYY-MM-DD.md`
4. **Update Project Note** — maintain `Projects/<Name>.md` with session log
5. **Extract Tech Stack** — classify mentioned technologies, update index
6. **Extract Q&A Pairs** — capture problems and solutions
7. **Generate Wiki Links** — link dates, projects, technologies
8. **Maintain Knowledge Graph** — write graph edges and node registry

## Directory

```
obsidian-second-brain/
├── skill.md                  # ⭐ Core: AI reads this and works
├── scripts/
│   ├── search_vault.py       # Find Obsidian vaults on disk
│   └── validate_vault.py     # Check vault health
├── templates/
│   ├── daily.md
│   ├── project.md
│   └── knowledge.md
└── README.md
```

## Requirements

- Python 3.9+ (stdlib only, no dependencies)
- Obsidian vault with `.obsidian` directory

## License

MIT
