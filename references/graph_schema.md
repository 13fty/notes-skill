# Knowledge Graph Schema

The ontology that defines what nodes and edges mean in the agent-knowledge system. Scripts (`graph_update.py`) and the AI both reference this schema for consistent graph construction.

## Table of Contents

- [Node Types](#node-types)
- [Edge Types](#edge-types)
- [Edge Detection Conditions](#edge-detection-conditions)
- [Cross-Project Inference](#cross-project-inference)

---

## Node Types

| Type | Kind | Description | Examples |
|------|------|-------------|----------|
| `language` | Technology | Programming language | Python, TypeScript, Rust |
| `framework` | Technology | Application framework or library ecosystem | FastAPI, React, PyQt5 |
| `tool` | Technology | Standalone tool or service | Docker, Git, GitHub Actions |
| `api_service` | Technology | External API or cloud service | OpenAI, AWS, Anthropic |
| `library` | Technology | Importable code package | Pydantic, OpenCV, NumPy |
| `concept` | Technology | Abstract technical concept or pattern | REST, RAG, microservices |
| `project` | Context | A named project in the vault | MyAPI, WeatherTracker |
| `person` | Context | A person mentioned in sessions | (future use) |

### Node naming convention

- Technology nodes: use the canonical name, e.g. `FastAPI` (not `fastapi`), `TypeScript` (not `typescript`)
- Project nodes: match the project note filename, e.g. `MyAPI` maps to `Projects/MyAPI.md`
- Concept nodes: capitalize as proper nouns, e.g. `REST`, `GraphQL`

---

## Edge Types

| Edge | Direction | Meaning |
|------|-----------|---------|
| `used-in` | Tech → Project | A technology/language/framework/tool is used in a project |
| `evolved-from` | Project → Project | This project was built on top of / forked from an earlier project |
| `inspired-by` | Project → Project | This project takes design ideas or patterns from another |
| `shares-stack-with` | Project ↔ Project | Two projects share ≥2 overlapping tech stack items |
| `depends-on` | Project → Project | This project requires another project to function (e.g., shared library, API) |
| `solved-by` | Problem → Tech/Approach | A specific problem was resolved by a technique or tool |

### Edge naming convention

- Use lowercase with hyphens: `used-in`, `shares-stack-with`
- Direction matters: `A used-in B` means A is a tech used in project B, NOT the reverse

---

## Edge Detection Conditions

### `used-in`

**Auto-detected** whenever a technology is mentioned in a project session.

```
Session mentions "FastAPI" + project is "MyAPI"
→ [[FastAPI]] used-in [[MyAPI]]
```

One edge per tech per project per session. Dedup by `(Source, Relation, Target)`.

### `evolved-from`

**Signal**: User says "based on X", "building on X", "forked from X", "using X as a base".

```
User: "This new API is based on the old AuthService we built last year"
→ [[NewAPI]] evolved-from [[AuthService]]
```

Requires both projects to have existing project notes.

### `inspired-by`

**Signal**: User says "similar to X", "like X", "inspired by X".

```
User: "I want a dashboard like the one in WeatherTracker"
→ [[NewDashboard]] inspired-by [[WeatherTracker]]
```

### `shares-stack-with`

**Auto-detected** by scanning all project notes and finding ≥2 overlapping technologies.

```
MyAPI: Python, FastAPI, Docker, OpenAI
WeatherTracker: TypeScript, FastAPI, Docker, AWS
Overlap: FastAPI, Docker (count = 2)
→ [[MyAPI]] shares-stack-with [[WeatherTracker]]
→ [[WeatherTracker]] shares-stack-with [[MyAPI]]
```

### `depends-on`

**Signal**: User describes a dependency chain: "X needs Y to run", "X is the backend for Y".

```
User: "MyAPI is the backend for the mobile app"
→ [[MobileApp]] depends-on [[MyAPI]]
```

### `solved-by`

**Auto-detected** when a problem-solution pair is extracted and the solution names a specific technology.

```
Problem: "Docker container can't find pydantic"
Solution: "Add pydantic to requirements.txt"
→ [[pydantic-missing]] solved-by [[Pydantic]]
```

---

## Cross-Project Inference

Every sync, `graph_update.py` scans all project notes for cross-project signals:

1. **Tech overlap**: Count shared technologies between current project and each existing project
2. **Threshold**: ≥2 shared tech items → `shares-stack-with` edge
3. **Explicit mentions**: Scan for project names mentioned in the current session
4. **Evolution chains**: If project A → B and B → C, infer A → C (transitive)

### Writing cross-project relations

In the Project Note under `## Related Projects`:

```markdown
- [[OtherProject]] — `shares-stack-with` (Python, FastAPI)
- [[OldProject]] — `evolved-from`
- [[LibraryProject]] — `depends-on`
```

Format: `- [[TargetProject]] — \`relation-type\` (detail)`
