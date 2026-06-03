# Examples

## Input → Output: A Real Session

**Conversation snippet:**

```
User: 我在用 FastAPI 写一个 API，Docker 部署，但是 uvicorn 启动时报错
"ModuleNotFoundError: No module named 'pydantic'"，怎么解决？

AI: 这是因为 Docker 镜像里没装 pydantic。在 requirements.txt 里加上 pydantic，
然后重新 docker build。另外确认你的 Dockerfile 里有 RUN pip install -r requirements.txt。

User: 好了，解决了！现在 API 跑起来了。下一步我想加上 OpenAI 的接口调用。
```

---

## What Gets Produced

### Daily Note (`Daily/2026-06-03.md`) — appended under `## AI Sessions`:

```markdown
> [!summary]- 14:30 · FastAPI 部署调试 · [[MyAPI]]
> FastAPI + Docker 部署中遇到 pydantic 缺失问题，已通过更新 requirements.txt 解决。
> 下一步集成 OpenAI 接口。
> **Tech**: FastAPI, Docker, Uvicorn, Pydantic, OpenAI
> **Tags**: #debug #deployment
```

### Project Note (`Projects/MyAPI.md`) — prepended under `## Session Log`:

```markdown
### 2026-06-03 · FastAPI 部署调试
> [[Daily/2026-06-03]] · ~30 min

解决了 Docker 环境中 pydantic 缺失导致的 uvicorn 启动失败。更新了 requirements.txt。
下一步计划集成 OpenAI API。

**Changes**:
- 修复: requirements.txt 添加 pydantic
- 新增: 计划集成 OpenAI 接口

**Open Issues**: none
```

### Tech Stack table (in Project Note):

```markdown
| Category | Technologies |
|----------|-------------|
| Language | Python |
| Framework | FastAPI |
| Tool | Docker · Uvicorn |
| API/Service | OpenAI |
| Library | Pydantic |
```

### Q&A entry (in Project Note `## Problems & Solutions`):

```markdown
### Docker 容器 uvicorn 启动报 ModuleNotFoundError

**Date**: 2026-06-03
**Context**: FastAPI 项目 Docker 部署时，uvicorn 启动找不到 pydantic 模块。

**Problem**:
Docker 镜像中未安装 pydantic，导致 uvicorn 启动报 ModuleNotFoundError。

**Solution**:
在 requirements.txt 中添加 pydantic，确保 Dockerfile 包含 pip install -r requirements.txt，
重新 docker build 即可。

**Tags**: #docker #pydantic #debug
```

### Tech Stack Index (`Meta/Tech Stack Index.md`) — merged entries:

```markdown
## FastAPI
- Used in: [[MyAPI]]
- Last seen: 2026-06-03

## Docker
- Used in: [[MyAPI]]
- Last seen: 2026-06-03

## Pydantic
- Used in: [[MyAPI]]
- Last seen: 2026-06-03

## OpenAI
- Used in: [[MyAPI]]
- Last seen: 2026-06-03
```

### Knowledge Graph (`Meta/Knowledge Graph.md`) — appended edges:

```markdown
| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|
| [[FastAPI]] | used-in | [[MyAPI]] | 2026-06-03 | [[Daily/2026-06-03]] |
| [[Docker]] | used-in | [[MyAPI]] | 2026-06-03 | [[Daily/2026-06-03]] |
| [[Pydantic]] | used-in | [[MyAPI]] | 2026-06-03 | [[Daily/2026-06-03]] |
| [[OpenAI]] | used-in | [[MyAPI]] | 2026-06-03 | [[Daily/2026-06-03]] |
```
