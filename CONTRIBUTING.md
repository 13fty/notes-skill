# Contributing

Thanks for your interest in contributing to Notes Skill! This project follows a lightweight contribution process.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/notes-skill.git`
3. Create a branch: `git checkout -b my-feature`

## Development

No external dependencies are required — the scripts use Python 3.9+ stdlib only.

To verify your changes work:

```bash
# Test extraction with sample input
echo "Implemented a FastAPI endpoint for user auth. Fixed a Docker build issue." | python scripts/extract.py

# Test with --dry-run (requires a configured vault)
python scripts/write_vault.py --input extracted.json --dry-run
python scripts/graph_update.py --input extracted.json --dry-run
```

## Pull Request Process

1. Keep changes focused — one PR, one concern
2. Follow the existing code style (stdlib-only Python, no external packages)
3. Update relevant documentation in `references/` if you change templates or rules
4. Add test cases to `evals/evals.json` for new extraction patterns
5. Open a PR with a clear description of what changed and why

## Reporting Issues

Use the issue templates when reporting bugs or requesting features. Include:
- What you were doing
- What you expected
- What happened instead
- Your Python version and OS

## Code Philosophy

- **Stdlib only**: No external Python packages. This keeps deployment trivial.
- **Append-only writes**: The vault write system must never delete or overwrite user content outside designated merge sections.
- **Scripts handle determinism, AI handles semantics**: Scripts do JSON parsing, file I/O, and dedup. The AI agent handles project name inference, tech classification, and relation inference.
