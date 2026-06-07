# Note Templates

Templates and reference material for the notes-skill system. Follows the 3-layer
architecture from `obsidian-note-framework.md`: **Session → Project → Knowledge**.

## Table of Contents

- [Vault Directory Structure](#vault-directory-structure)
- [Template: Session Log](#template-session-log)
- [Template: Daily Note](#template-daily-note)
- [Template: Project Note](#template-project-note)
- [Template: Knowledge Node](#template-knowledge-node)
- [Template: Knowledge Graph](#template-knowledge-graph)
- [Template: Projects Index](#template-projects-index)
- [Tech Classification Rules](#tech-classification-rules)
- [Change / Problem / Solution Detection](#change--problem--solution-detection)
- [Graph Schema](#graph-schema)
- [Project Name Inference](#project-name-inference)
- [Naming Conventions](#naming-conventions)

---

## Vault Directory Structure

```
{VaultRoot}/
│
├── Sessions/                        ← 会话记录（主入口，每次 Agent 会话一条）
│   ├── 2026-06-07-1430.md
│   └── 2026-06-07-0915.md
│
├── Projects/                        ← 项目笔记（每个项目一个文件）
│   ├── AgentWatch.md
│   └── notes-skill.md
│
├── Daily/                           ← 日记（按天聚合，表格形式）
│   ├── 2026-06-07.md
│   └── 2026-06-06.md
│
├── Knowledge/                       ← 知识节点（概念、工具、框架、模式）
│   ├── Unix-Domain-Socket.md
│   ├── IPC.md
│   └── SwiftUI.md
│
└── Meta/                            ← 元数据索引
    ├── Knowledge-Graph.md           ← 知识节点关系表
    └── Projects-Index.md            ← 项目总览
```

### 三层信息流

```
① 会话层 (Sessions/)      这次 Agent 做了什么？
         │
         ├──→ ② 项目层 (Projects/)   这个项目的全部历史？
         ├──→ ② 项目层 (Daily/)      今天做了哪些事？
         └──→ ③ 知识层 (Knowledge/)  这个知识点是什么？
```

### Safety Constraints

1. **Append-only**: Never delete or overwrite existing content outside of designated merge sections
2. **Merge sections**: Project Changelog, Knowledge Node 踩坑记录/与其他概念的关系 — add rows, never remove
3. **User territory**: Content outside designated auto-maintained sections is user territory — never modify

---

## Template: Session Log

**Path**: `<vault>/Sessions/YYYY-MM-DD-HHMM.md`
**Naming**: `2026-06-07-1430.md` (date + 24h time, no topic slug)

```markdown
---
date: {{date}}
time: {{time}}
duration: {{duration_min}}min
project: {{project_name}}
type: {{coding|debugging|learning|design}}
tags: [{{comma_separated_tags}}]
---

# {{date}} {{time}} · {{project_name}} · {{one_line_summary}}

## 📁 项目

[[Projects/{{project_name}}]] · {{modified_files}}

## ✏️ 修改了什么

### 新增

- `{{file}}` — {{what_it_does}}

### 修改

- `{{file}}` — {{what_changed}}

### 删除

- `{{file}}` — {{why_removed}}

## 💬 对话摘要

{{2-3 sentence summary of the conversation and decisions made}}

## 🔗 涉及的知识点

| 知识点 | 关系 | 备注 |
|--------|------|------|
| [[Knowledge/{{concept_name}}]] | 核心机制 | 本次新学 |
| [[Knowledge/{{concept_name}}]] | 父概念 | {{note}} |
| [[Knowledge/{{concept_name}}]] | 相关 | {{note}} |

## ❓ 遗留问题

- [ ] {{unresolved_issue}}

## ✅ 本次收获

- {{key_takeaway}}
```

### Rules

- **Append-only** — wrong turns and dead ends are preserved as process history
- If no files were deleted, omit the "删除" section
- If no problems encountered, omit "❓ 遗留问题"
- Knowledge table rows: relation is one of `核心机制 | 父概念 | 相关 | 同类 | 对比`
- `type` field: pick the closest match — `coding` (implementation), `debugging` (bug fixing), `learning` (research/exploration), `design` (architecture/planning)

---

## Template: Daily Note

**Path**: `<vault>/Daily/YYYY-MM-DD.md`

```markdown
---
date: {{date}}
tags: [daily]
---

# {{date}} {{weekday}}

## Sessions

<!-- 当天所有 Agent 会话，按时间顺序追加新行 -->

| 时间 | 项目 | 做了什么 | 时长 |
|------|------|----------|------|
| 09:15 | [[Projects/{{project}}]] | {{one_line_summary}} | {{duration}}min |
| 14:30 | [[Projects/{{project}}]] | {{one_line_summary}} | {{duration}}min |

## Wins Today

- {{achievement_or_breakthrough}}

## Blockers

- {{blocking_issue}}

## Notes

{{freeform_notes}}
```

### Rules

- Append a new row to the Sessions table for each agent session
- Keep each "做了什么" cell to ≤60 chars — detail lives in `Sessions/`
- Wins/Blockers/Notes are for user reflection; AI may leave them blank
- Sessions table preserves chronological order

---

## Template: Project Note

**Path**: `<vault>/Projects/{{project_name}}.md`

```markdown
---
status: {{active|paused|completed}}
created: {{date}}
updated: {{date}}
tech: [{{comma_separated_tech_list}}]
tags: [project, {{additional_tags}}]
---

# {{project_name}}

## Overview

{{one paragraph describing what this project is and why it exists}}

## Tech Stack

| 类别 | 技术 |
|------|------|
| 语言 | |
| 框架 | |
| 通信 | |
| 工具 | |

## Changelog

<!-- 最新在前，由 Agent 会话自动追加 -->

### {{date}} · {{one_line_summary}}

> [[Sessions/{{session_file}}]] · {{duration}}min

{{2-3 sentence description}}

**修改文件：** `{{file1}}` `{{file2}}` `{{file3}}`
**遗留：** {{open_issues_from_session}}

---

## Open Issues

<!-- 汇总所有会话遗留的未解决问题 -->

- [ ] {{issue_description}}

## Related Sessions

<!-- 全部会话，按时间倒序 -->

- [[Sessions/{{session_file}}]] · {{one_line_summary}}
- [[Sessions/{{session_file}}]] · {{one_line_summary}}

## Knowledge Nodes

<!-- 该项目涉及的所有知识点，自由链接 -->

[[Knowledge/{{concept}}]] · [[Knowledge/{{concept}}]] · [[Knowledge/{{concept}}]]
```

### Rules

- **Changelog entries** are prepended (newest first)
- Each changelog entry **must** list modified files and any open issues
- Tech Stack uses freeform categories — pick categories that fit the project
- `status` lifecycle: `active` → `paused` → `completed`

---

## Template: Knowledge Node

**Path**: `<vault>/Knowledge/{{ConceptName}}.md`
**Naming**: Kebab-case, e.g. `Unix-Domain-Socket.md`, `IPC.md`

```markdown
---
type: {{concept|tool|framework|pattern}}
tags: [{{comma_separated_tags}}]
first_seen: {{date}}
---

# {{ConceptName}}

## 一句话

{{one-line: what it is and why it matters}}

## 核心机制

- {{mechanism_1}}
- {{mechanism_2}}
- {{mechanism_3}}

## 代码片段

```{{language}}
{{minimal_working_example}}
```

## 与其他概念的关系

- 父概念：[[Knowledge/{{parent_concept}}]]
- 同类机制：[[Knowledge/{{sibling_concept}}]]（{{brief_comparison}}）
- 对比：{{alternative}} — {{tradeoff}}
- 在项目中使用：[[Projects/{{project_name}}]]

## 踩坑记录

| 日期 | 问题 | 解决方式 |
|------|------|----------|
| {{date}} | {{problem_description}} | {{solution_summary}} |

## 来源会话

[[Sessions/{{source_session}}]]
```

### Merge strategy (when knowledge node already exists)

| Section | Behavior |
|---------|----------|
| 一句话 | **Never touch** — user may have refined it |
| 核心机制 | **Never touch** — user's curated understanding |
| 代码片段 | **Never touch** — user's preferred example |
| 与其他概念的关系 | **Append** new relations if not listed |
| 踩坑记录 | **Append** new rows to the table |
| 来源会话 | **Append** new session link if not listed |

### Knowledge Node types

| type | Description | Examples |
|------|-------------|----------|
| `concept` | Abstract technical concept or principle | IPC, RAG, PTY |
| `tool` | Standalone tool or service | Docker, Git, GitHub Actions |
| `framework` | Application framework or library ecosystem | FastAPI, React, SwiftUI |
| `pattern` | Design pattern, architecture decision, or best practice | append-only writes, CQRS |

---

## Template: Knowledge Graph

**Path**: `<vault>/Meta/Knowledge-Graph.md`

```markdown
---
tags: [meta, graph]
---

# Knowledge Graph

所有知识节点之间的关系表，兼容 Dataview 插件查询。

## 关系表

| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|
| [[Knowledge/UDS]] | used-in | [[Projects/AgentWatch]] | 2026-06-07 | [[Sessions/2026-06-07-1430]] |
| [[Knowledge/IPC]] | parent-of | [[Knowledge/UDS]] | 2026-06-07 | [[Sessions/2026-06-07-1430]] |

## 关系类型

| Relation | Meaning |
|----------|---------|
| `used-in` | Knowledge node used in a project |
| `parent-of` | Parent concept → child concept |
| `related-to` | Two knowledge nodes are related |
| `evolved-from` | Project built on top of an earlier one |
| `shares-stack-with` | Two projects share ≥2 tech items |
```

### Rules

- Append edges, dedup by `(Source, Relation, Target)` triple
- Source/Target use `[[Knowledge/...]]` or `[[Projects/...]]` links
- One `used-in` edge per knowledge node per project per session

---

## Template: Projects Index

**Path**: `<vault>/Meta/Projects-Index.md`

```markdown
---
tags: [meta, index]
---

# Projects Index

所有项目的总览表。

| Project | Status | Tech | Updated |
|---------|--------|------|---------|
| [[Projects/AgentWatch]] | active | Swift, SwiftUI, Python | 2026-06-07 |
| [[Projects/notes-skill]] | active | Python, Markdown | 2026-06-07 |

<!-- Rows merged by notes-skill -->
```

### Rules

- If project exists in table → update `Updated` date and `Tech` list
- If project is new → append a new row
- Never remove rows

---

## Tech Classification Rules

### Language
`Python` `TypeScript` `JavaScript` `Swift` `Rust` `Go` `Kotlin` `Java` `C++` `C#` `Ruby` `PHP` `Bash` `Shell`

### Framework
`FastAPI` `Flask` `Django` `React` `Vue` `Next.js` `Nuxt` `PyQt5` `PyQt6` `SwiftUI` `UIKit` `Express` `NestJS` `Spring` `Rails` `Laravel`

### Tool
`Docker` `Git` `npm` `pip` `Homebrew` `Make` `Webpack` `Vite` `Pytest` `Jest` `GitHub Actions` `Nginx` `Caddy`

### API / Service
`Anthropic` `OpenAI` `DeepSeek` `Gemini` `Claude` `WeChat` `Telegram` `Slack` `AWS` `GCP` `Azure` `Vercel` `Railway`

### Library
`OpenCV` `MediaPipe` `NumPy` `Pandas` `Matplotlib` `SQLAlchemy` `Pydantic` `Uvicorn` `aiohttp` `requests` `Tailwind` `shadcn`

### Concept
`REST` `GraphQL` `WebSocket` `gRPC` `IPC` `PTY` `MVC` `MVVM` `microservices` `RAG` `embeddings` `LLM` `AI agent`

### Extending the lists

If a technology appears but is NOT in these lists, add it to the most appropriate category. The lists are starting points, not exhaustive.

---

## Change / Problem / Solution Detection

### Change signals (Chinese)
`新增了` `实现了` `修复了` `重构了` `改进了` `添加了` `删除了` `优化了` `完成了` `部署了`

### Change signals (English)
`added` `implemented` `fixed` `refactored` `improved` `removed` `optimized` `built` `created` `deployed` `updated` `migrated`

### Problem signals (Chinese)
`报错` `错误` `问题` `怎么` `为什么` `如何` `坏了` `不行` `出问题了` `失败`

### Problem signals (English)
`error` `Error` `Exception` `issue` `bug` `not working` `doesn't work` `failed` `why is` `why does` `how do` `how can` `broken` `crash`

### Solution signals (Chinese)
`解决了` `工作了` `成功了` `修复` `搞定` `好了` `可以了` `办法是`

### Solution signals (English)
`fix` `fixed` `solution` `resolved` `solved` `try` `instead` `should` `workaround` `the fix is`

### Q&A pairing logic
1. When a problem signal is found, look ahead up to 20 lines / 3 paragraphs for a solution signal
2. If found → pair as Q&A, add to Session Log's "涉及的知识点" and Knowledge Node's "踩坑记录"
3. If NOT found → add to Session Log's "❓ 遗留问题"
4. Cap at 5 problem-solution pairs per session

---

## Graph Schema

### Edge Types

| Edge | Direction | Meaning |
|------|-----------|---------|
| `used-in` | Knowledge → Project | A knowledge node is used in a project |
| `parent-of` | Knowledge → Knowledge | Parent concept → child concept |
| `related-to` | Knowledge ↔ Knowledge | Two knowledge nodes are related |
| `evolved-from` | Project → Project | This project was built on top of an earlier one |
| `shares-stack-with` | Project ↔ Project | Two projects share ≥2 tech items |

### Cross-Project Inference

1. **Tech overlap**: Count shared technologies between current project and each existing project
2. **Threshold**: ≥2 shared tech items → `shares-stack-with` edge
3. **Evolution chains**: If project A → B and B → C, infer A → C (transitive)

Writing format in Project Note under `## Open Issues` and `## Related Sessions` (auto-maintained).

---

## Project Name Inference

Priority order:

1. **Explicit declaration**: User says "this is project X", "my project is called Y"
2. **Codebase reference**: Agent mentions working in `/path/to/project-name/`
3. **Repository name**: `git remote -v` or folder name in conversation
4. **Markdown heading**: The first `# Heading` that looks like a project name
5. **Fallback**: `通用` (General)

If multiple projects are mentioned, return the primary one (most lines of conversation about it).

---

## Naming Conventions

| 类型 | 格式 | 示例 |
|------|------|------|
| Session | `YYYY-MM-DD-HHMM` | `2026-06-07-1430` |
| Project | PascalCase | `AgentWatch`, `notes-skill` |
| Daily | `YYYY-MM-DD` | `2026-06-07` |
| Knowledge | Kebab-case | `Unix-Domain-Socket`, `IPC` |
| Meta | Kebab-case or Title Case | `Knowledge-Graph`, `Projects-Index` |

---

## Tag Inference

| Keyword / Tech | Tag |
|---------------|-----|
| Docker, deploy, 部署 | `#deployment` |
| Error, bug, 报错, fix, debug | `#debug` |
| API, endpoint, route | `#api` |
| Database, SQL, 数据库 | `#database` |
| UI, frontend, component | `#ui` |
| Test, 测试, pytest, jest | `#testing` |
| Auth, login, 登录 | `#auth` |
| Performance, 性能, optimize | `#performance` |
