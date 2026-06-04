# Knowledge Extraction Rules

How to classify technologies, detect changes, and extract problems/solutions from agent session conversations.

## Table of Contents

- [Tech Classification](#tech-classification)
- [Change Detection Signals](#change-detection-signals)
- [Problem Detection Signals](#problem-detection-signals)
- [Solution Detection Signals](#solution-detection-signals)
- [Project Name Inference](#project-name-inference)
- [Importance Rating](#importance-rating)

---

## Tech Classification

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

If a technology appears in conversation but is NOT in these lists, add it to the most appropriate category. The lists are starting points, not exhaustive.

---

## Change Detection Signals

### Chinese signals (change happened)
`新增了` `实现了` `修复了` `重构了` `改进了` `添加了` `删除了` `优化了` `完成了` `部署了`

### English signals (change happened)
`added` `implemented` `fixed` `refactored` `improved` `removed` `optimized` `built` `created` `deployed` `updated` `migrated`

### Extraction rules for changes
1. Scan each line for change signals
2. Capture the full sentence as the change description
3. Cap at 10 changes per session
4. Prefer specific descriptions: "fixed Docker build by adding pydantic to requirements.txt" over "fixed bug"

---

## Problem Detection Signals

### Chinese (a problem was encountered)
`报错` `错误` `问题` `怎么` `为什么` `如何` `坏了` `不行` `出问题了` `失败`

### English (a problem was encountered)
`error` `Error` `Exception` `issue` `bug` `not working` `doesn't work` `failed` `why is` `why does` `how do` `how can` `broken` `crash`

### Extraction rules for problems
1. When a problem signal is found, look ahead up to 20 lines for a **solution signal**
2. If found → pair them as a problem-solution
3. If NOT found → mark as an open issue
4. Extract the surrounding context (±2 lines) as the problem description
5. Cap at 5 problem-solution pairs per session

---

## Solution Detection Signals

### Chinese (problem was resolved)
`解决了` `工作了` `成功了` `修复` `搞定` `好了` `可以了` `办法是`

### English (problem was resolved)
`fix` `fixed` `solution` `resolved` `solved` `try` `instead` `should` `workaround` `the fix is`

### Extraction rules for solutions
1. The solution is usually 1-3 lines describing what was done
2. If the solution includes a code block, capture it verbatim
3. Infer tags from the problem domain (see tag inference below)

---

## Project Name Inference

Priority order for determining project name:

1. **Explicit declaration**: User says "this is project X", "my project is called Y"
2. **Codebase reference**: Agent mentions working in `/path/to/project-name/`
3. **Markdown heading**: The first `# Heading` that looks like a project name
4. **Repository name**: `git remote -v` or folder name in conversation
5. **Fallback**: `通用` (General)

If multiple projects are mentioned, return the primary one (most lines of conversation about it). List others in `related_projects` field.

---

## Tag Inference

From tech stack and problem domain, infer tags:

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

---

## Note Type Detection

Beyond basic extraction, the system detects which *additional* note types should be created from a session. This is how the `note_types` field in the extraction JSON is populated.

### Snippet Detection

A session line or code block is snippet-worthy when:

| Signal | Weight |
|--------|--------|
| Code block ≥5 lines that's not boilerplate (imports, config) | High |
| Code preceded by "here's how", "用法", "示例", "the trick is" | High |
| User says "save this", "记住这个", "这个有用", "this is useful" | High |
| Agent writes a non-trivial function or workaround | Medium |
| Code block + explanation pattern (code then 2-3 lines of explanation) | Medium |

Extract as:
```json
{
  "type": "snippet",
  "title": "descriptive-slug-title",
  "language": "python",
  "code": "full code block",
  "caveats": ["caveat 1", "caveat 2"],
  "primary_tech": "TechName"
}
```

### Concept Note Detection

A concept is worth a standalone note when:

| Signal | Example |
|--------|---------|
| User asks "what is X", "X 是什么", "explain X" | "WebSocket 和长轮询有什么区别？" |
| Agent explains an abstract principle | "IPC 的本质是操作系统在两个进程间传递数据" |
| An abstract technical term first appears and gets explained | IPC, RAG, PTY, embeddings |
| User says "我理解了", "原来如此", "that makes sense" after explanation | Concept internalized |
| Term appears in Concept category of tech stack | Refer to `extract_rules.md` Concept list |

Extract as:
```json
{
  "type": "concept",
  "name": "ConceptName",
  "core_idea": "one-sentence summary",
  "understanding": "1 paragraph in your own words",
  "domain": "backend",
  "related": ["RelatedConcept1", "RelatedConcept2"]
}
```

### Tech Card Detection

Create or update a Tech Card when:

| Signal | Action |
|--------|--------|
| Tech detected that is NOT in `<vault>/Meta/Tech Stack Index.md` | Create stub Tech Card (first use) |
| Code block using a library's non-obvious API | Add to "核心用法" section |
| Error message + tech name + fix combination | Append to "踩过的坑" section |
| User says "以后还会用", "记住这个", "下次参考" | Set `priority: high` |
| Agent says "this is the standard way to..." | Add to "核心用法" |

Extract as:
```json
{
  "type": "tech_card",
  "name": "TechName",
  "category": "framework",
  "description": "one-line what and why",
  "version": "0.104.x",
  "new_pitfalls": ["pitfall description"],
  "is_first_use": true
}
```

### ADR Detection

Create an Architecture Decision Record when:

| Signal | Confidence |
|--------|------------|
| "放弃 A，改用 B" / "dropped A in favor of B" | High |
| "因为...所以选了..." / "because...we chose..." | High |
| Mention of ≥2 alternatives with explicit tradeoff discussion | High |
| "以后都用", "标准做法定为" / "going forward we'll use X" | Medium |
| "为什么选 X 而不是 Y" / "why X over Y" | High |
| Agent: "the reason I chose X is..." followed by a rationale | Medium |

Extract as:
```json
{
  "type": "adr",
  "title": "Short decision title",
  "background": "1 paragraph context",
  "problem": "specific problem statement",
  "options": [
    {"name": "Option A", "status": "chosen"},
    {"name": "Option B", "status": "rejected"}
  ],
  "chosen": "Option A",
  "reasons": ["reason 1", "reason 2"],
  "tradeoffs": ["cost of the decision"]
}
```

---

## Importance Rating

Rate each extraction by importance to prioritize what gets written:

| Level | Criteria |
|-------|----------|
| **High** | New project created, major bug fixed, new tech introduced, architecture change |
| **Medium** | Feature implemented, code refactored, library added, Q&A resolved |
| **Low** | Minor tweak, configuration change, discussion, exploration |

High and Medium items always get written to vault. Low items are written only if they relate to an existing project note.
