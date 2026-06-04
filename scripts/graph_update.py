#!/usr/bin/env python3
"""Update the Knowledge Graph and Node registry in the Obsidian vault.

Reads the extraction JSON and:
  - Appends edges to Meta/Knowledge Graph.md (dedup by Source+Relation+Target)
  - Updates Meta/Nodes.md with node type and project associations
  - Infers cross-project relations by scanning existing project notes

Usage:
    python scripts/graph_update.py --input /tmp/extracted.json
    python scripts/graph_update.py --input extracted.json --dry-run
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "vault_config.json"

# ── Graph Schema ─────────────────────────────────────────────────────────────

NODE_TYPES = {
    "Language": "language",
    "Framework": "framework",
    "Tool": "tool",
    "API": "api_service",
    "Library": "library",
    "Concept": "concept",
}

EDGE_TYPES = {
    "used-in": "Tech/library used in a project",
    "evolved-from": "Project built on top of an earlier one",
    "inspired-by": "Project takes ideas from another",
    "shares-stack-with": "Two projects share ≥2 tech items",
    "depends-on": "Project requires another to function",
    "solved-by": "Problem solved by a particular approach/tech",
}


def load_config() -> dict:
    """Load vault configuration."""
    if not CONFIG_FILE.exists():
        print(f"Config not found: {CONFIG_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def today_str() -> str:
    """Return today's date string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── Knowledge Graph ──────────────────────────────────────────────────────────

def knowledge_graph_template() -> str:
    """Knowledge Graph file template."""
    return """---
tags: [meta, graph]
---

# Knowledge Graph

Machine-readable edges between all nodes in the vault.
Compatible with Dataview plugin for queries.

## Edges

| Source | Relation | Target | Date | Project |
|--------|----------|--------|------|---------|

## Relations

| Relation | Meaning |
|----------|---------|
| `used-in` | Tech/library used in a project |
| `evolved-from` | Project built on top of an earlier one |
| `inspired-by` | Project takes ideas from another |
| `shares-stack-with` | Two projects share ≥2 tech items |
| `depends-on` | Project requires another to function |
| `solved-by` | Problem solved by a particular approach/tech |

## Notes
- All nodes should also appear in `[[Meta/Nodes]]`
"""


def nodes_template() -> str:
    """Nodes registry template."""
    return """---
tags: [meta, nodes]
---

# Nodes

Canonical registry of all knowledge graph nodes.

| Node | Type | First Seen | Projects |
|------|------|-----------|---------|

<!-- Entries merged here by agent-knowledge -->
"""


def update_knowledge_graph(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> list[str]:
    """Append edges to the Knowledge Graph. Deduplicate by (Source, Relation, Target)."""
    graph_path = Path(vault_path) / "Meta" / "Knowledge Graph.md"

    if not graph_path.exists():
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(knowledge_graph_template(), encoding="utf-8")

    project = data.get("project_name", "通用")
    tech_stack = data.get("tech_stack", {})
    new_edges = []

    # Generate used-in edges for each tech
    for category, techs in tech_stack.items():
        for tech in techs:
            edge = f"| [[{tech}]] | used-in | [[{project}]] | {date_str} | [[{project}]] |"
            new_edges.append(edge)

    if dry_run:
        return [f"[DRY RUN] Would add {len(new_edges)} edges to {graph_path}"]

    content = graph_path.read_text(encoding="utf-8")

    # Dedup — check existing edges
    existing_edges = set()
    for line in content.split("\n"):
        if line.startswith("| ") and " | " in line:
            parts = line.split(" | ")
            if len(parts) >= 3:
                # Normalize: strip brackets for comparison
                src = parts[0].strip("| ").replace("[[", "").replace("]]", "")
                rel = parts[1].strip()
                tgt = parts[2].strip().replace("[[", "").replace("]]", "")
                existing_edges.add((src, rel, tgt))

    added = 0
    for edge in new_edges:
        parts = edge.split(" | ")
        if len(parts) >= 3:
            src = parts[0].strip("| ").replace("[[", "").replace("]]", "")
            rel = parts[1].strip()
            tgt = parts[2].strip().replace("[[", "").replace("]]", "")
            if (src, rel, tgt) not in existing_edges:
                content += edge + "\n"
                existing_edges.add((src, rel, tgt))
                added += 1

    graph_path.write_text(content, encoding="utf-8")
    return [f"Added {added} new edges to Knowledge Graph (skipped {len(new_edges) - added} duplicates)"]


def update_nodes(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> list[str]:
    """Update the Nodes registry with new tech nodes."""
    nodes_path = Path(vault_path) / "Meta" / "Nodes.md"

    if not nodes_path.exists():
        nodes_path.parent.mkdir(parents=True, exist_ok=True)
        nodes_path.write_text(nodes_template(), encoding="utf-8")

    project = data.get("project_name", "通用")
    tech_stack = data.get("tech_stack", {})

    if dry_run:
        return [f"[DRY RUN] Would update Nodes registry at {nodes_path}"]

    content = nodes_path.read_text(encoding="utf-8")

    for category, techs in tech_stack.items():
        node_type = NODE_TYPES.get(category, "unknown")
        for tech in techs:
            # Check if node already exists
            if f"| [[{tech}]] |" not in content:
                # Add new node entry
                content += f"| [[{tech}]] | {node_type} | {date_str} | [[{project}]] |\n"
            else:
                # Update project list if this project isn't listed yet
                for line in content.split("\n"):
                    if line.startswith(f"| [[{tech}]] |"):
                        if f"[[{project}]]" not in line:
                            # Append project
                            new_line = line.rstrip() + f", [[{project}]]"
                            content = content.replace(line, new_line)
                        break

    nodes_path.write_text(content, encoding="utf-8")
    return [f"Updated Nodes registry"]


def infer_cross_project_relations(vault_path: str, data: dict, date_str: str, dry_run: bool = False) -> list[str]:
    """Scan existing project notes and infer cross-project relationships."""
    projects_dir = Path(vault_path) / "Projects"
    if not projects_dir.exists():
        return ["No Projects/ directory — skipping cross-project inference."]

    current_project = data.get("project_name", "通用")
    current_tech = set()
    for techs in data.get("tech_stack", {}).values():
        current_tech.update(t.lower() for t in techs)

    if not current_tech or current_project == "通用":
        return ["Skipping cross-project inference (no tech or generic project)."]

    results = []

    for proj_file in projects_dir.glob("*.md"):
        proj_name = proj_file.stem
        if proj_name == current_project:
            continue

        proj_content = proj_file.read_text(encoding="utf-8")
        proj_tech = set()

        # Extract tech from project note's Tech Stack table
        for line in proj_content.split("\n"):
            if line.startswith("| ") and " | " in line:
                techs_in_row = re.findall(r"`?(\w[\w\s-]+\w)`?", line)
                for t in techs_in_row:
                    t = t.strip()
                    if len(t) > 1 and t not in ("Category", "Technologies", "Language", "Framework", "Tool", "API", "Library", "Concept"):
                        proj_tech.add(t.lower())

        # Check for ≥2 overlapping tech items
        overlap = current_tech & proj_tech
        if len(overlap) >= 2:
            results.append({
                "source": f"[[{current_project}]]",
                "relation": "shares-stack-with",
                "target": f"[[{proj_name}]]",
                "detail": f"({', '.join(sorted(overlap)[:3])})",
            })

    # Write inferred relations to current project note
    if results and not dry_run:
        proj_path = projects_dir / f"{current_project}.md"
        if proj_path.exists():
            content = proj_path.read_text(encoding="utf-8")
            if "## Related Projects" in content:
                for rel in results:
                    rel_line = f"- {rel['target']} — `{rel['relation']}` {rel['detail']}"
                    if rel_line not in content:
                        parts = content.split("## Related Projects", 1)
                        after = parts[1]
                        # Insert after ## Related Projects header
                        next_section = _find_next_section(after)
                        if next_section >= 0:
                            content = (
                                parts[0]
                                + "## Related Projects"
                                + after[:next_section]
                                + rel_line
                                + "\n"
                                + after[next_section:]
                            )
                        else:
                            content = parts[0] + "## Related Projects\n" + rel_line + "\n" + after
            proj_path.write_text(content, encoding="utf-8")

    if dry_run:
        return [f"[DRY RUN] Would infer {len(results)} cross-project relations"]
    return [f"Inferred {len(results)} cross-project relations"]


def _find_next_section(text: str) -> int:
    """Find the index of the next ## heading."""
    m = re.search(r"\n## ", text)
    return m.start() if m else -1


def main():
    input_path = None
    dry_run = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_path = args[i + 1]
            i += 2
        elif args[i].startswith("--input="):
            input_path = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            i += 1

    if not input_path:
        print("Usage: python scripts/graph_update.py --input <extracted.json> [--dry-run]", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    vault_path = config["vault_path"]
    date_str = today_str()

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []

    # 1. Knowledge Graph edges
    results.extend(update_knowledge_graph(vault_path, data, date_str, dry_run))

    # 2. Nodes registry
    results.extend(update_nodes(vault_path, data, date_str, dry_run))

    # 3. Cross-project relations
    results.extend(infer_cross_project_relations(vault_path, data, date_str, dry_run))

    print("\n".join(results))
    if not dry_run:
        print(f"\nGraph updated: {vault_path}")


if __name__ == "__main__":
    main()
