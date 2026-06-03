# Obsidian Second Brain

An AI agent skill that processes conversation sessions and syncs structured knowledge into an [Obsidian](https://obsidian.md) vault.

## Quick Start

Register `SKILL.md` as a custom skill. The first time it runs, it will guide you through vault setup.

```bash
# Find your vault
python scripts/helper.py --json

# Validate a vault
python scripts/validator.py --path ~/Documents/Obsidian

# Set config (or let the AI do it)
mkdir -p ~/.obsidian-skill
echo '{"vault_path": "/path/to/your/vault"}' > ~/.obsidian-skill/config.json
```

## Directory

```
my-skill/
├── SKILL.md              # ⭐ Entry point — AI reads this first
├── docs/
│   ├── workflow.md       # Detailed 8-step workflow
│   ├── examples.md       # Real input → output examples
│   └── faq.md            # Edge cases and troubleshooting
├── templates/
│   ├── output.md         # Daily Note template
│   ├── report.md         # Project Note template
│   └── knowledge.md      # Knowledge Graph template
├── scripts/
│   ├── helper.py         # Find Obsidian vaults on disk
│   └── validator.py      # Check vault health
├── assets/
│   └── references.md     # Tech classification and reference tables
└── README.md
```

## Requirements

- Python 3.9+ (stdlib only)
- Obsidian vault with `.obsidian` directory
