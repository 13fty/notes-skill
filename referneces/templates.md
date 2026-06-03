# Obsidian Note Templates

Full Markdown templates for all note types managed by the Obsidian skill.

---

## Daily Note Template
**Path**: `Daily/YYYY-MM-DD.md`

```markdown
---
tags: [daily]
date: {{date}}
---

# {{date:dddd, MMMM D, YYYY}}

## Focus
> What matters most today?

- 

## Today's Progress
- [ ] 

## AI Sessions

<!-- Sessions appended here by skill -->

## Action Items
- [ ] 

## Notes & Thoughts

---
*Created by Obsidian Skill*
```

---

## Project Note Template
**Path**: `Projects/{ProjectName}.md`

```markdown
---
tags: [project]
status: active
created: {{date}}
updated: {{date}}
tech: []
---

# {ProjectName}

## Overview
> One paragraph description of what this project is and why it exists.

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Language | |
| Framework | |
| Tool | |
| API | |

## Session Log

<!-- Newest entries first -->

## Problems & Solutions

<!-- Q&A pairs appended here -->

## Related Projects

<!-- Associations auto-generated -->

## Knowledge Nodes

<!-- Graph references -->

---
*Last synced: {{date}}*
```

---

## Tech Stack Index Template
**Path**: `Meta/Tech Stack Index.md`

```markdown
---
tags: [meta, index]
---

# Tech Stack Index

Index of all technologies encountered across projects, auto-maintained by the Obsidian skill.

<!-- Entries sorted alphabetically by tech name -->
```

---

## Q&A Archive Template
**Path**: `Meta/QA Archive.md`

```markdown
---
tags: [meta, qa]
---

# Q&A Archive

All extracted problem/solution pairs, newest first.

<!-- Entries appended by skill -->
```

---

## Knowledge Graph Template
**Path**: `Meta/Knowledge Graph.md`

```markdown
---
tags: [meta, graph]
---

# Knowledge Graph

Machine-readable edges between all nodes in the vault.
Compatible with Dataview plugin for queries.

## Edges

| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|

## Notes
- Relations: `used-in`, `evolved-from`, `inspired-by`, `shares-stack-with`, `depends-on`
- All nodes should also appear in `[[Meta/Nodes]]`
```

---

## Nodes Registry Template
**Path**: `Meta/Nodes.md`

```markdown
---
tags: [meta, nodes]
---

# Node Registry

All named entities tracked in the knowledge graph.

| Node | Type | First Seen | Projects |
|------|------|-----------|---------|
```

---

## Stub Note Template
**Path**: `{any missing link target}.md`

```markdown
---
tags: [stub]
created: {{date}}
---

# {Title}

> [!note] Stub — to be filled in
> This note was auto-created by the Obsidian skill as a link target.
> Fill in content when you have time.
```