# Changelog

All notable changes to the Notes Skill project.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Full vault write pipeline with `write_vault.py` (Daily Notes, Project Notes, Tech Index, QA Archive)
- Knowledge graph system with `graph_update.py` (edge dedup, node registry, cross-project inference)
- First-time setup wizard with `setup.py` (vault discovery, validation, bootstrapping)
- Structured extraction engine with `extract.py` (tech classification, change detection, problem-solution pairing)
- Note type detection: snippets, concept notes, tech cards, ADRs
- Sub-agent definition for complex session extraction
- Reference documentation: templates, extraction rules, graph schema, vault structure
- Evaluation test cases in `evals/evals.json`
- Auto-trigger heuristics for session completion detection
- Append-only vault write guarantees

### Changed

- Reorganized from single-file skill to modular structure (scripts/, references/, agents/, evals/, config/)
- SKILL.md rewritten as mode router (SETUP vs SYNC)
- README updated with Quick Start, pipeline diagram, and directory structure

### Removed

- Old monolithic helper scripts (`helper.py`, `validator.py`)
- Old docs directory (`docs/workflow.md`, `docs/examples.md`, `docs/faq.md`)
- Old templates (`templates/knowledge.md`, `templates/output.md`, `templates/report.md`)

## [0.1.0] — 2026-06-04

### Added

- Initial project structure with SKILL.md entry point
- Python stdlib-only constraint (3.9+)
- MIT License
- Basic `.gitignore`
