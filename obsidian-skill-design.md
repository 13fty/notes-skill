# Obsidian Note-Taking Agent Skill — 完整设计文档

> **文档目的**：全面描述该 Skill 的设计理念、文件结构、各组件功能，以及文件之间的依赖与数据流关系。读完此文档，你应当能够独立理解、复现或扩展这个 Skill。

---

## 目录

1. [设计理念](#1-设计理念)
2. [Skill 文件结构总览](#2-skill-文件结构总览)
3. [文件关系图](#3-文件关系图)
4. [核心文件详解：SKILL.md](#4-核心文件详解skillmd)
5. [辅助脚本详解：scripts/](#5-辅助脚本详解scripts)
6. [模板文件详解：references/templates.md](#6-模板文件详解referencestemplatesmd)
7. [Vault 输出结构](#7-vault-输出结构)
8. [端到端数据流](#8-端到端数据流)
9. [各组件职责边界](#9-各组件职责边界)
10. [扩展与改进方向](#10-扩展与改进方向)

---

## 1. 设计理念

### 1.1 核心问题

AI Agent（如 Claude）在与用户进行多轮对话、修改文件、调试代码的过程中，产生了大量有价值的知识：解决方案、技术决策、问题排查过程。这些知识分散在对话流中，**不记录则永久消失**。

### 1.2 Skill 的定位

这个 Skill 是一个**知识提炼与持久化管道**，它做三件事：

```
原始对话 / 文件变更
        │
        ▼
  ① 结构化提炼
  （摘要、技术栈、Q&A、关系）
        │
        ▼
  ② 写入 Obsidian Vault
  （日记、项目笔记、元数据索引）
        │
        ▼
  ③ 构建知识图谱
  （节点注册、边关系、Wiki 链接）
```

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **非破坏性写入** | 所有操作是 append 或 section-replace，永不覆盖整个文件 |
| **双语友好** | 中英文关键词均有检测规则，适配中文用户 |
| **渐进加载** | SKILL.md 控制主流程，脚本和模板按需读取，避免上下文膨胀 |
| **Vault 可移植** | 输出为标准 Markdown + Dataview 兼容格式，不依赖特定插件 |
| **人工可覆盖** | 所有输出均可手动编辑，Skill 不做破坏性假设 |

---

## 2. Skill 文件结构总览

```
obsidian/                          ← Skill 根目录
│
├── SKILL.md                       ← ★ 主控文件（Agent 的行动指南）
│
├── references/
│   └── templates.md               ← Vault 各类笔记的 Markdown 模板库
│
└── scripts/
    ├── sync.py                    ← 将 Claude 输出写入本地 Vault 的同步工具
    └── parse_session.py           ← 从对话文本中提取结构化数据的解析库
```

**三层加载机制**（Progressive Disclosure）：

```
层级 1：SKILL.md frontmatter（name + description）
  → 始终在 Agent 上下文中，约 100 词
  → 决定 Skill 何时被触发

层级 2：SKILL.md 主体（8个步骤的处理规则）
  → Skill 触发时加载，< 500 行
  → Agent 的完整行动指南

层级 3：references/ 和 scripts/（模板 + 脚本）
  → 按需读取，不限大小
  → scripts 可直接执行，无需加载到上下文
```

---

## 3. 文件关系图

### 3.1 Skill 内部文件关系

```
┌─────────────────────────────────────────────────────────────┐
│                        SKILL.md                             │
│                    （主控 + 步骤规则）                        │
│                                                             │
│  Step 1: 生成摘要                                            │
│  Step 2: 更新日记  ──── 使用 templates.md → Daily 模板       │
│  Step 3: 更新项目  ──── 使用 templates.md → Project 模板     │
│  Step 4: 提取技术栈 ─── 调用 parse_session.py               │
│  Step 5: 提取 Q&A  ──── 调用 parse_session.py               │
│  Step 6: 生成链接  ──── 调用 parse_session.py               │
│  Step 7: 项目关联                                            │
│  Step 8: 知识图谱  ──── 使用 templates.md → Graph 模板       │
│           │                                                  │
│           └─ 输出 obsidian-file 块 ──► sync.py 写入 Vault    │
└─────────────────────────────────────────────────────────────┘
         ↑ 触发时读取                    ↑ 需要时读取
```

### 3.2 Vault 内部笔记关系

```
                    ┌──────────────────┐
                    │  Daily/          │
                    │  YYYY-MM-DD.md   │
                    │  （日记）         │
                    └────────┬─────────┘
                             │ [[链接]]
                             ▼
              ┌──────────────────────────┐
              │  Projects/               │
              │  {ProjectName}.md        │◄──────────────────┐
              │  （项目笔记）             │                    │
              └──────────────────────────┘                    │
                 ↗ 使用        ↘ 关联                         │
┌─────────────────────┐   ┌─────────────────────┐            │
│  Meta/              │   │  Meta/              │            │
│  Tech Stack Index   │   │  QA Archive.md      │            │
│  （技术索引）        │   │  （问答归档）         │            │
└─────────────────────┘   └─────────────────────┘            │
              ↑                      ↑                        │
              │ 节点引用              │ 来源标注               │
              ▼                      ▼                        │
┌──────────────────────────────────────────────┐             │
│  Meta/Knowledge Graph.md  （知识图谱边表）    │─────────────┘
│  Meta/Nodes.md            （节点注册表）      │
└──────────────────────────────────────────────┘
              ↑
              │ 生成 Stub
              ▼
┌──────────────────────────────────────────────┐
│  Tech/{TechName}.md  /  People/{Name}.md     │
│  （自动创建的 Stub 占位笔记）                  │
└──────────────────────────────────────────────┘
```

---

## 4. 核心文件详解：SKILL.md

SKILL.md 是整个 Skill 的**大脑**，包含两个部分：

### 4.1 YAML Frontmatter（触发元数据）

```yaml
---
name: obsidian
description: >
  Process AI agent conversation sessions and sync structured knowledge into Obsidian vaults.
  触发词包括："save to obsidian"、"update my notes"、"log this session"、
  "add to daily note"、"记录一下"、"整理笔记" 等。
---
```

**作用**：Agent 根据 `description` 判断是否触发此 Skill。描述故意设计得"主动"（pushy），包含大量触发短语，以避免 undertrigger 问题。

### 4.2 主体：8 步处理流程

每个步骤的功能与输入输出如下：

---

#### Step 1 — 生成会话摘要

**输入**：原始对话文本 / 文件变更记录  
**输出**：结构化摘要块（≤ 20 行）

**摘要 Schema**：
```
主题 / 项目 / 持续时间 / 核心产出（≤5条）/ 未解决问题 / 下一步行动
```

**规则**：
- 使用过去时（"解决了"、"实现了"）
- 不在摘要中嵌入原始代码块（代码放到 Project Note）
- 作为后续所有步骤的基础输入

---

#### Step 2 — 更新 Daily Note

**目标文件**：`{vault}/Daily/YYYY-MM-DD.md`  
**操作**：append（不覆盖）

```
读取现有文件（或从模板创建）
    │
    ├── 找到 ## AI Sessions 区块 → 追加 callout 折叠块
    ├── 更新 ## Today's Progress → 勾选已完成项
    └── 追加 ## Action Items → 添加新的 checkbox
```

**输出格式**（Obsidian callout 语法）：
```markdown
> [!summary]- HH:mm · {Session Topic} · [[{ProjectName}]]
> {摘要内容}
> **Tech**: python · fastapi
> **Tags**: #ai #backend
```

**冲突处理**：若 `## AI Sessions` 已存在 → append；不存在 → 在文件末创建该节。

---

#### Step 3 — 更新 Project Note

**目标文件**：`{vault}/Projects/{ProjectName}.md`  
**操作**：在 `## Session Log` 顶部插入（最新优先）

**Project Note 结构**（首次创建时使用模板）：
```
YAML frontmatter（tags, status, created, updated）
# ProjectName
## Overview
## Tech Stack      ← Step 4 填充
## Session Log     ← Step 3 维护，最新在前
## Problems & Solutions  ← Step 5 填充
## Related Projects      ← Step 7 填充
## Knowledge Nodes       ← Step 8 填充
```

**Session Log Entry 格式**：
```markdown
### YYYY-MM-DD · {Session Topic}
> [[Daily/YYYY-MM-DD]] · ~45 min
{摘要段落}
**Changes**: - ...
**Open Issues**: none
```

---

#### Step 4 — 提取技术栈

**输入**：对话文本  
**处理**：`parse_session.py` 中的 `extract_tech_stack()` 函数  
**输出位置**：
1. Project Note 的 `## Tech Stack` 表格
2. `{vault}/Meta/Tech Stack Index.md`（全局索引，去重合并）

**检测范围**（6 大类）：
```
Language   → Python, TypeScript, Swift, Go, Rust ...
Framework  → FastAPI, React, PyQt5, SwiftUI ...
Tool       → Docker, Git, npm, Homebrew ...
API/Service→ Anthropic, DeepSeek, OpenAI, WeChat ...
Library    → OpenCV, MediaPipe, NumPy, python-pptx ...
Concept    → REST, IPC, PTY, RAG, LLM agent ...
```

**全局索引格式**：
```markdown
## {TechName}
- Used in: [[ProjectA]], [[ProjectB]]
- Last seen: YYYY-MM-DD
- Notes: {版本或用法备注}
```

---

#### Step 5 — 提取问答对（Q&A）

**输入**：对话文本  
**处理**：`parse_session.py` 中的 `extract_qa_pairs()` 函数  
**输出位置**：
1. Project Note 的 `## Problems & Solutions`
2. `{vault}/Meta/QA Archive.md`（全局归档，逆序）

**触发信号检测**：
```
问题信号：error:、报错、问题、why is、how to、怎么、为什么、not working ...
解答信号：fix、solution、resolved、solved、解决了、工作了、try: ...
```

**配对逻辑**：发现问题段落后，向前看最多 3 个段落寻找解答。匹配成功则生成 QAPair 对象。

**Q&A Entry 格式**：
```markdown
### {短标题（问题前8词）}
**Date**: YYYY-MM-DD
**Project**: [[ProjectName]]
**Problem**: {描述}
**Solution**: {描述或代码块}
**Tags**: #tag1 #tag2
```

---

#### Step 6 — 自动生成 Wiki 链接

**输入**：生成的笔记文本  
**处理**：`parse_session.py` 中的 `linkify()` 函数

**链接规则表**：

| 条件 | 转换结果 |
|------|----------|
| 日期 `YYYY-MM-DD` | `[[Daily/YYYY-MM-DD]]` |
| 已知项目名 | `[[Projects/ProjectName]]` |
| Tech Stack Index 中的技术 | `[[Tech/TechName]]` 或内联 tag |
| 已知人名/团队 | `[[People/Name]]`（若笔记存在） |
| 同一笔记中第一次出现 | 生成链接；后续出现 → 纯文本 |

**Stub 创建**：链接目标不存在时，自动创建 Stub 占位笔记：
```markdown
---
tags: [stub]
created: YYYY-MM-DD
---
# {Title}
> [!note] Stub — to be filled in
```

---

#### Step 7 — 推断项目关联

**输入**：当前项目的技术栈 + 已知其他项目信息  
**输出位置**：Project Note 的 `## Related Projects`

**四种关联类型**：

| 触发条件 | 关联类型 |
|----------|----------|
| 技术栈重叠 ≥ 2 项 | `shares-stack-with` |
| 当前项目基于上一个项目构建 | `evolved-from` |
| 某库/工具首见于项目A，现出现于项目B | `uses`（指向该库） |
| 用户说"类似于 X" / "like X" | `inspired-by` |

**输出格式**：
```markdown
## Related Projects
- [[AgentWatch]] — `shares-stack-with` (Swift, SwiftUI)
- [[wxbot]] — `evolved-from` (Node.js + FastAPI)
```

---

#### Step 8 — 维护知识图谱

**输出文件**：
- `{vault}/Meta/Knowledge Graph.md` — 边关系表（Dataview 兼容）
- `{vault}/Meta/Nodes.md` — 节点注册表

**边格式**（只追加，按 Source + Relation + Target 去重）：
```markdown
| Source | Relation | Target | Date | Session |
|--------|----------|--------|------|---------|
| [[PyQt5]] | used-in | [[FingerCounter]] | 2025-06-01 | [[Daily/2025-06-01]] |
```

**关系类型词汇表**：
```
used-in          技术被用于某项目
evolved-from     项目从另一项目演化而来
inspired-by      设计受某项目/概念启发
shares-stack-with 两项目共用技术栈
depends-on       运行时依赖关系
```

**节点格式**：
```markdown
| Node | Type | First Seen | Projects |
|------|------|-----------|---------|
| [[PyQt5]] | framework | 2025-05-10 | [[FingerCounter]], [[DormManager]] |
```

---

## 5. 辅助脚本详解：scripts/

### 5.1 `scripts/parse_session.py`

**定位**：NLP 解析库，可独立运行或被 SKILL.md 步骤调用

**三大模块**：

#### 模块 A：技术栈提取

```python
TECH_REGISTRY = {
    "Language":  ["Python", "TypeScript", ...],
    "Framework": ["FastAPI", "PyQt5", ...],
    ...
}

def extract_tech_stack(text: str) -> dict[str, list[str]]:
    # 分词 → 小写匹配 → 返回 {类别: [技术名]}
```

- 维护一个扁平化查找表 `_TECH_LOOKUP`：`lowercase_name → (category, canonical_name)`
- 正则分词：`[\w.#/+\-]+`，处理带点号/井号的名称（如 `C#`、`Next.js`）

#### 模块 B：问答对提取

```python
PROBLEM_SIGNALS = [r"error[:\s]", r"报错", r"怎么", ...]
SOLUTION_SIGNALS = [r"fix(ed)?", r"解决了", r"成功了", ...]

def extract_qa_pairs(text: str) -> list[QAPair]:
    # 按空行分段 → 逐段匹配信号词 → 向前找解答段
```

- 使用 `@dataclass QAPair`：`title / problem / solution / tags`
- 问题段落后最多看 3 段寻找解答

#### 模块 C：Wiki 链接化

```python
def linkify(text, known_projects, vault_root=None) -> str:
    # 日期替换 → 项目名替换（最长匹配优先）→ 仅第一次出现
```

- 使用集合 `linked` 跟踪已链接实体，确保"第一次出现才链接"
- 项目名按长度降序排序，避免短名称干扰长名称

**CLI 用法**：
```bash
python parse_session.py --input session.txt --output parsed.json \
                        --project "FingerCounter" --date 2025-06-01
```

**输出 JSON 格式**：
```json
{
  "date": "2025-06-01",
  "project": "FingerCounter",
  "tech_stack": {"Framework": ["OpenCV", "PyQt5"]},
  "tech_markdown": "| Category | Technologies |\n...",
  "qa_pairs": [...],
  "qa_markdown": [...]
}
```

---

### 5.2 `scripts/sync.py`

**定位**：Vault 写入工具，将 Claude 输出的 `obsidian-file` 块同步到本地文件系统

**工作原理**：

```
Claude 输出 → 包含多个 obsidian-file 块
                    │
                    ▼
             parse_blocks()
             解析每个块的 header：path / action / section
                    │
                    ▼
             apply_block()
             根据 action 调用对应写入函数
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
  action_create  action_append  action_replace_section
  （仅新建）     （安全追加）    （精确替换指定节）
```

**`obsidian-file` 块格式**（Claude 输出标准）：
````
```obsidian-file
path: Daily/2025-06-03.md
action: append | create | replace-section
section: ## AI Sessions
---
{文件内容}
```
````

**三种操作模式**：

| Action | 行为 | 幂等性 |
|--------|------|--------|
| `create` | 仅当文件不存在时创建 | ✅ 安全 |
| `append` | 在指定节末追加（节不存在则创建） | ✅ 安全 |
| `replace-section` | 替换指定节的全部内容 | ⚠️ 需确认 |

**`append` 精确定位逻辑**：
```python
# 找到目标节（如 ## AI Sessions），
# 在下一个同级或更高级标题前插入内容
pattern = re.compile(
    r"(" + re.escape(section) + r"\n)(.*?)(\n#{1,level} |\Z)",
    re.DOTALL
)
```

**CLI 用法**：
```bash
# 从文件同步
python sync.py --vault ~/Documents/MyVault --input claude_output.md

# 从管道同步（典型工作流）
cat claude_output.md | python sync.py --vault ~/Documents/MyVault

# 预演（不写文件）
python sync.py --vault ~/Documents/MyVault --input output.md --dry-run
```

---

## 6. 模板文件详解：references/templates.md

**定位**：所有 Vault 笔记的 Markdown 模板库，在需要创建新文件时由 SKILL.md 引用

**包含 6 种模板**：

| 模板名 | 路径规则 | 用途 |
|--------|----------|------|
| Daily Note | `Daily/YYYY-MM-DD.md` | 每日日记骨架 |
| Project Note | `Projects/{Name}.md` | 项目笔记骨架 |
| Tech Stack Index | `Meta/Tech Stack Index.md` | 技术全局索引 |
| Q&A Archive | `Meta/QA Archive.md` | 问答全局归档 |
| Knowledge Graph | `Meta/Knowledge Graph.md` | 图谱边关系表 |
| Nodes Registry | `Meta/Nodes.md` | 图谱节点注册 |
| Stub Note | `{任意缺失链接目标}.md` | 占位笔记 |

**每个模板包含**：
- YAML frontmatter（tags、status、created、updated 等）
- 标准节结构（供 sync.py 的 `section` 参数精确定位）
- 注释占位符（`<!-- Entries appended here by skill -->`）

---

## 7. Vault 输出结构

Skill 运行后，Obsidian Vault 的文件布局：

```
{VaultRoot}/
│
├── Daily/
│   └── YYYY-MM-DD.md          ← 每日日记（Step 2 写入）
│
├── Projects/
│   └── {ProjectName}.md       ← 项目笔记（Step 3 写入）
│
├── Tech/
│   └── {TechName}.md          ← 技术 Stub 笔记（Step 6 自动创建）
│
├── People/
│   └── {Name}.md              ← 人物 Stub 笔记（Step 6 自动创建）
│
└── Meta/
    ├── Tech Stack Index.md    ← 所有技术的全局索引（Step 4 维护）
    ├── QA Archive.md          ← 所有问答对的全局归档（Step 5 维护）
    ├── Knowledge Graph.md     ← 图谱边关系表（Step 8 维护）
    └── Nodes.md               ← 节点注册表（Step 8 维护）
```

**笔记间的链接关系汇总**：

```
Daily Note
  └─ [[Projects/ProjectName]]        ← callout 中的项目引用

Project Note
  ├─ [[Daily/YYYY-MM-DD]]            ← Session Log 的来源日记
  ├─ [[Tech/TechName]]               ← Tech Stack 中的技术链接
  └─ [[Projects/RelatedProject]]     ← Related Projects 中的关联

Knowledge Graph
  ├─ [[Tech/X]] → used-in → [[Projects/Y]]
  ├─ [[Projects/A]] → evolved-from → [[Projects/B]]
  └─ 所有节点均引用自 Nodes.md
```

---

## 8. 端到端数据流

```
┌───────────────────────────────────────────────────────────┐
│  输入层                                                    │
│  ┌───────────────┐  ┌─────────────────┐                   │
│  │ 对话文本      │  │ 文件变更记录    │                   │
│  └───────┬───────┘  └────────┬────────┘                   │
└──────────┼──────────────────┼────────────────────────────┘
           │                  │
           └──────────┬───────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  SKILL.md 处理层                                            │
│                                                             │
│  Step 1: 生成摘要（Claude 理解 + 压缩）                     │
│                   │                                         │
│          ┌────────┼────────────────────────────┐           │
│          ▼        ▼                            ▼           │
│  Step 2        Step 3                       Step 4+5       │
│  生成日记文本  生成项目文本                调用 parse_session│
│          │        │                            │           │
│          └────────┴────────────────────────────┘           │
│                   │                                         │
│          Step 6: linkify()（wiki 链接化）                   │
│          Step 7: 推断项目关联                               │
│          Step 8: 生成图谱边                                 │
│                   │                                         │
│          输出 obsidian-file 块集合                          │
└───────────────────┬─────────────────────────────────────────┘
                    │
           ┌────────┴────────┐
           ▼                 ▼
    直接粘贴到 Vault       sync.py 自动写入
    （手动工作流）         （自动化工作流）
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Obsidian Vault                                             │
│  Daily/ · Projects/ · Meta/ · Tech/ · People/               │
│  （相互 [[WikiLink]] 连接的知识网络）                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. 各组件职责边界

| 组件 | 负责 | 不负责 |
|------|------|--------|
| `SKILL.md frontmatter` | 触发判断（何时使用此 Skill） | 任何处理逻辑 |
| `SKILL.md 主体` | 8步处理规则、输出格式、冲突策略 | 实际文件读写 |
| `parse_session.py` | 从文本提取结构化数据（技术、Q&A、链接） | 知道 Vault 的存在 |
| `sync.py` | 将 obsidian-file 块写入本地文件系统 | 理解内容含义 |
| `templates.md` | 提供新文件的初始骨架 | 维护现有文件 |
| `Knowledge Graph.md` | 存储边关系（机器可读） | 可视化渲染 |
| `Nodes.md` | 节点注册与首次出现追踪 | 边关系存储 |

---

## 10. 扩展与改进方向

### 10.1 功能扩展

| 方向 | 建议实现位置 |
|------|-------------|
| 支持 Cursor / Windsurf 的文件变更 diff 提取 | `parse_session.py` 新增 `extract_file_changes()` |
| 自动生成 Mermaid 关系图 | `SKILL.md` 新增 Step 9，生成 `.mermaid` 文件 |
| 支持语音备忘录转写 | `parse_session.py` 新增预处理管道 |
| Obsidian Canvas 节点布局 | 新增 `scripts/canvas_builder.py` |
| 定期 Digest（周报/月报） | 新增 `scripts/digest.py`，查询 Knowledge Graph 聚合 |

### 10.2 现有局限

| 局限 | 说明 |
|------|------|
| Q&A 提取为启发式 | 基于信号词匹配，对自然语言对话效果有限 |
| 技术栈词典需手动维护 | 新技术（如 Bun、Deno）需手动加入 `TECH_REGISTRY` |
| 不支持双向同步 | 只能从 Claude → Vault 单向写入，Vault 修改不回流 |
| 中文分词未使用专用库 | 依赖空格分隔，对无空格中文句子的实体提取有限 |

### 10.3 文件扩展示例

若要新增"代码变更追踪"功能，在现有结构中：

```
obsidian/
├── SKILL.md                    ← 添加 Step 9：提取文件变更
├── references/
│   └── templates.md            ← 添加 File Change Log 模板
└── scripts/
    ├── sync.py                 （不变）
    ├── parse_session.py        ← 添加 extract_file_changes() 函数
    └── diff_tracker.py         ← 新增：解析 git diff / patch 格式
```

---

## 附录：输出完整性检查清单

运行 Skill 后，确认以下 8 项均已完成：

```
□ 1. Session Summary 已生成（≤ 20 行，过去时）
□ 2. Daily Note 已更新（section 追加，未覆盖）
□ 3. Project Note 已更新（Session Log 最新在前）
□ 4. Tech Stack 表格已更新（项目笔记 + 全局索引，去重）
□ 5. Q&A 对已提取（写入项目笔记 + QA Archive）
□ 6. 所有专有名词已 [[WikiLink]] 化（缺失目标已创建 Stub）
□ 7. 项目关联已推断并写入（shares-stack / evolved-from 等）
□ 8. 知识图谱边已追加（Nodes.md 节点已注册，去重）
```

---

*文档版本：v1.0 · 基于 obsidian skill 当前实现分析生成*
