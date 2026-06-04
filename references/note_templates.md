# Note Templates

Markdown templates for every note type written by the noteskill system. The pipeline routes extracted knowledge to the appropriate template based on the `note_types` field in the extraction JSON.

## Table of Contents

- [Routing Table](#routing-table)
- [Session Log（任务日志）](#session-log)
- [Snippet（代码片段）](#snippet)
- [Concept Note（概念笔记）](#concept-note)
- [Tech Card（技术卡）](#tech-card)
- [ADR（架构决策记录）](#adr)
- [Daily Note](#daily-note)
- [Project Note](#project-note)
- [Tech Stack Table](#tech-stack-table)
- [Tech Stack Index Entry](#tech-stack-index-entry)
- [QA Archive Entry](#qa-archive-entry)
- [Knowledge Graph](#knowledge-graph)
- [Nodes Registry](#nodes-registry)

---

## Routing Table

Which template the agent picks based on extracted signals:

| Note Type | `type` field | When to create | File location |
|-----------|-------------|----------------|---------------|
| Session Log | `session` | Every agent task end — highest frequency | `<vault>/Sessions/YYYY-MM-DD-{topic}.md` |
| Snippet | `snippet` | Code block ≥5 lines that solves a specific problem | `<vault>/Snippets/{descriptive-name}.md` |
| Concept Note | `concept` | New technical concept or principle discussed | `<vault>/Concepts/{ConceptName}.md` |
| Tech Card | `tech_card` | First time a tool/framework/library is used | `<vault>/Tech/{TechName}.md` |
| ADR | `adr` | Architecture-level decision with tradeoffs | `<vault>/Decisions/ADR-{###}-{title}.md` |

---

## Session Log

File: `<vault>/Sessions/YYYY-MM-DD-{topic-slug}.md`

The core note type — one per agent task session. Based on juhis's "running notes" pattern: append-only, preserves wrong turns as process history.

```markdown
---
tags: [session, agent-log]
project: "[[Projects/{{project_name}}]]"
date: {{date}}
updated: {{date}}
tech: [{{tech_list_json}}]
type: session
---

# {{date}} · {{session_topic}}

## 做了什么
{{#each changes}}
- {{this}}
{{/each}}

## 关键决策
> {{key_decision_quote}}
> 为什么：{{rationale}}

## 遇到的问题 & 解法
{{#each problems_solved}}
**问题**：{{problem}}
**解法**：{{solution}}

{{/each}}

## 用到的技术
{{#each tech_stack_flat}}
[[{{tech_name}}]]{{#unless @last}} · {{/unless}}
{{/each}}

## 遗留问题
{{#each open_issues}}
- [ ] {{this}}
{{/each}}

## 关联
← [[Projects/{{project_name}}]]  ← [[Daily/{{date}}]]
```

Rules:
- **Append-only** — even if wrong turns were taken, keep them as process history
- **Cross-link** to Project Note and Daily Note at bottom
- **Tech list** uses Wiki Links for graph connectivity
- If no problems were solved, omit "遇到的问题 & 解法" section
- If no open issues, write "无"

---

## Snippet

File: `<vault>/Snippets/{descriptive-slug}.md`

One snippet = one specific usage of a tool or technique. juhis describes this as "a note per single usage of a tool or technique" — it gradually becomes your personal Stack Overflow.

```markdown
---
tags: [snippet]
tech: "[[{{primary_tech}}]]"
context: "[[Projects/{{project_name}}]]"
date: {{date}}
works_on: [{{platforms}}]
type: snippet
---

# {{descriptive_title}}

## 场景
{{1-2 sentences: when do you need this?}}

## 代码
```{{language}}
{{code_block}}
```

## 注意
{{#each caveats}}
- {{this}}
{{/each}}

## 来源
[[Sessions/{{source_session}}]]
```

Rules:
- **Title format**: `{Tool} {Action}` — e.g. "PTY 写入 stdin 的正确方式", "Git branch column display"
- **Code block**: Must include language tag for syntax highlighting
- **Caveats**: Edge cases, platform-specific notes, common gotchas
- **Single purpose**: If a snippet does two unrelated things, split into two notes
- **Dedup**: Check `<vault>/Snippets/` for an existing snippet with the same title before creating

### Detection signals for snippet-worthy code

| Signal | Weight |
|--------|--------|
| Code block ≥5 lines | High |
| Code block preceded by "here's how", "用法", "示例" | High |
| Code contains non-trivial logic (not just imports/config) | Medium |
| User says "save this", "记住这个", "这个有用" | High |

---

## Concept Note

File: `<vault>/Concepts/{ConceptName}.md`

Zettelkasten atomic unit — expresses a single idea and links to related concepts. Based on Niklas Luhmann's method: one note = one thought, written in your own words, heavily interlinked.

```markdown
---
tags: [concept]
domain: [{{primary_domain}}]
date: {{date}}
type: concept
---

# {{ConceptName}}

## 核心思想
{{1-2 sentences: the central idea in your own words}}

## 常见方式对比
| 方式 | 延迟 | 适用场景 |
|------|------|---------|
| {{variant_1}} | {{latency}} | {{use_case}} |

## 我的理解
{{1 paragraph: internalize the concept — how would you explain it to a colleague?}}

## 在哪里用过
{{#each used_in_projects}}
- [[Projects/{{this}}]] — {{brief_context}}
{{/each}}

## 关联概念
{{#each related_concepts}}
[[{{this}}]]{{#unless @last}} · {{/unless}}
{{/each}}

## 来源
[[Sessions/{{source_session}}]]
```

Rules:
- **One concept per note** — split compound topics into separate notes
- **"我的理解" section is mandatory** — this is the Zettelkasten "write in your own words" principle
- **"在哪里用过" section** — links theory to practice; agent appends when concept reappears
- **"关联概念" section** — minimum 3 links; this is how the knowledge graph grows
- If an existing Concept Note already covers this topic, merge into it rather than creating a duplicate

### Merge strategy (when concept already exists)

When a concept note already exists and a new session mentions the same concept, the agent
follows a **targeted append-only** strategy:

| Section | Merge behavior | Rationale |
|---------|---------------|-----------|
| 核心思想 | **Never touch** | User may have refined the explanation |
| 常见方式对比 | **Never touch** | User's curated comparison table |
| 我的理解 | **Never touch** | This is the user's personal internalization — sacred |
| 关联概念 | **Never touch** | User's curated link network |
| 在哪里用过 | **Append** new project+date line if not listed | Accumulates usage history |
| 来源 | **Append** new session link if not listed | Accumulates reference trail |

This ensures:
- User's manually written body content is never overwritten
- The note doesn't grow unboundedly (only lists grow, and they grow slowly)
- The knowledge graph stays up-to-date (new usage is recorded)
- Merges are idempotent (checking "if not listed" before appending)

---

## Tech Card

File: `<vault>/Tech/{TechName}.md`

One note per technology (tool, framework, library). Aggregates all knowledge about that tech across projects. Inspired by the "software learning template" pattern.

```markdown
---
tags: [tech-card]
type: technology
category: {{category}}
status: active
first_used: {{date}}
last_used: {{date}}
---

# {{TechName}}

## 一句话描述
{{one-line: what it is and why you use it}}

## 用过的版本
`{{version}}`

## 核心用法
```{{language}}
{{minimal_working_example}}
```

## 踩过的坑
{{#each pitfalls}}
- {{this}}
{{/each}}

## 参考资料
- [{{link_label}}]({{url}})
{{#each related_snippets}}
- [[Snippets/{{this}}]]
{{/each}}

## 用在哪些项目
```dataview
LIST FROM [[]] WHERE contains(tech, "{{TechName}}")
```

## 来源
[[Sessions/{{source_session}}]]
```

Rules:
- **First-use auto-create**: When `extract.py` detects a tech NOT in `<vault>/Meta/Tech Stack Index.md`, create a stub Tech Card
- **Update on reuse**: If the tech appears again, update `last_used` and append to "踩过的坑" if new issues arose
- **Status lifecycle**: `learning` → `active` → `deprecated` (if replaced)
- **"踩过的坑" section**: Append-only — this is personal battle-scar knowledge
- If user explicitly asks to "save this for next time" with a tech, mark it `priority: high`

### Detection signals

| Signal | Action |
|--------|--------|
| `first_used` date not in Meta/Tech Stack Index | Create stub Tech Card automatically |
| Code block using a library's non-obvious API | Add to "核心用法" |
| Error message + tech name + fix | Append to "踩过的坑" |
| User says "以后还会用", "记住这个用法" | Mark as high priority |

---

## ADR

File: `<vault>/Decisions/ADR-{{###}}-{{slug}}.md`

Architecture Decision Record — captures *why* a choice was made, not just what was chosen. Based on the ADR pattern popularized by Michael Nygard. Eric Ma emphasizes linking to source material for verifiability.

```markdown
---
tags: [ADR]
project: "[[Projects/{{project_name}}]]"
date: {{date}}
status: {{status}}
superseded_by: null
type: decision
---

# ADR-{{###}} · {{decision_title}}

## 背景
{{1 paragraph: what was the situation that required a decision?}}

## 问题
{{1-2 sentences: the specific problem or constraint}}

## 考虑的方案
1. {{option_1}}（{{status_1}}）
2. {{option_2}}（{{status_2}}）
3. {{option_3}}（{{status_3}}）

## 决定
选方案 {{chosen_option}}。

## 原因
{{#each reasons}}
- {{this}}
{{/each}}

## 代价 / 权衡
{{#each tradeoffs}}
- {{this}}
{{/each}}

## 关联 session
[[Sessions/{{source_session}}]]

## 关联 ADR
{{#each related_adrs}}
- [[Decisions/ADR-{{###}}-{{title}}]]
{{/each}}
```

Status values: `proposed` | `accepted` | `deprecated` | `superseded`

When superseded, set `status: superseded` and `superseded_by: "ADR-###"`.

Rules:
- **Number sequentially**: Scan `<vault>/Decisions/` for the highest ADR number, increment by 1
- **Status starts as `accepted`** (we only record decisions after they're made)
- **"考虑的方案" must include ≥2 alternatives** — an ADR with only one option isn't a decision
- **If the decision is reversed later**: Don't edit the original. Create a new ADR that supersedes the old one
- **Always link source session**: This is the "source material" Eric Ma emphasizes for verifiability

### Detection signals (explicit trigger — not auto-detected)

ADR creation is **explicit, not automatic**. The agent asks the user proactively when it
detects a significant architecture choice. See `SKILL.md § Explicit Triggers` for the protocol.

When the agent does invoke ADR creation, these signals help confirm it's worth asking:

| Signal | Confidence |
|--------|------------|
| "放弃 A，改用 B" / "dropped A in favor of B" | High — ask user |
| "因为...所以选了..." / "because...we chose..." | High — ask user |
| Mention of ≥2 alternatives with tradeoff discussion | Medium — ask user |
| "以后都用", "标准做法定为" / "going forward we'll use" | Medium — ask user |
| User explicitly says "记成 ADR" / "log this decision" | Highest — create immediately |

---

## Daily Note

File: `<vault>/Daily/YYYY-MM-DD.md`

The Daily Note is a **lightweight day overview**. Each session gets a brief callout
(≤5 lines) linking to the full session log in `Sessions/`.

**Division of labor with Sessions/:**

| What | Where | Content |
|------|-------|---------|
| Day overview (light) | `Daily/YYYY-MM-DD.md` | One callout per session (3-5 lines) + tech tags |
| Session detail (full) | `Sessions/YYYY-MM-DD-{topic}.md` | Complete changes, decisions, problems, code |

Do NOT write full session detail into Daily — keep it light. Link to Sessions/ instead.

```markdown
---
tags: [daily]
date: {{date}}
---

# {{date}}

## Focus
> What matters most today?

-

## Today's Progress
- [ ]

## AI Sessions

<!-- Brief callouts appended here by noteskill — one per session -->

## Action Items
- [ ]

## Notes & Thoughts

---
*Created by noteskill*
```

### Session callout (appended under `## AI Sessions`)

Brief summary only — the full session detail lives in `Sessions/`:

```markdown
> [!summary]- HH:mm · {{session_topic}} · [[{{project_name}}]]
> {{one_paragraph_summary}}
> **Tech**: {{comma_separated_tech_tags}}
> **Tags**: #{{tag1}} #{{tag2}}
> 📄 [[Sessions/{{session_filename}}|Full session log →]]
```

Rules:
- Always **append** below existing entries — never overwrite
- Keep each callout to ≤5 lines — the detail belongs in `Sessions/`
- **Must** include a `[[Sessions/...]]` link to the full session log
- If multiple projects in one session, list all project links in the callout

---
## Project Note

File: `<vault>/Projects/{{project_name}}.md`

```markdown
---
tags: [project]
status: active
created: {{date}}
updated: {{date}}
tech: []
---

# {{project_name}}

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

## ADR Index

<!-- Links to ADRs for this project -->

---
*Last synced: {{date}}*
```

---

## Tech Stack Table, Index, QA Archive, Knowledge Graph, Nodes

These remain unchanged — see [references/graph_schema.md](graph_schema.md) and [references/vault_structure.md](vault_structure.md) for the maintained formats.
