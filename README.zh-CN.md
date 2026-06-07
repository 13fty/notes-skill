# Notes Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org/)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen.svg)](https://github.com)

> 📖 [English version](README.md)

一个 AI agent 技能，可在每次 agent 任务完成后自动 hook，将结构化知识同步到 [Obsidian](https://obsidian.md) 笔记库中。与手动触发的笔记工具不同，本系统在完成实质性的编码、调试或设计会话后**自动触发**——提取学到的内容并持久化，无需用户手动操作。

## 设计理念

- **自动触发**：agent 任务完成后自动运行，不依赖用户手动请求
- **3 层笔记框架**：会话层 → 项目层 → 知识层 —— 从原始对话到可复用知识的清晰信息流
- **8 步 AI 驱动流水线**：摘要 → 日记 → 项目笔记 → 知识节点 → 问答 → Wiki 链接 → 项目关联 → 知识图谱
- **仅追加写入**：绝不删除或覆盖用户已有内容；所有写入均为追加或节级合并
- **统一知识节点**：一种模板覆盖全部知识类型（概念/工具/框架/模式）—— 替代了分散的代码片段、概念笔记、技术卡片、架构决策模板
- **双语支持**：中英文信号词检测，覆盖技术分类、问题/解答配对和变更追踪
- **跨项目感知**：自动推断项目之间的关联关系（技术重叠、演进链等）
- **持续增长**：知识图谱边随时间累积；用得越久，信息越丰富

## 快速开始

### 环境要求

- Python 3.9+（仅依赖标准库，无需 pip 安装任何包）
- 一个包含 `.obsidian` 目录的 [Obsidian](https://obsidian.md) 笔记库
- 对笔记库路径有写入权限

### 安装

1. **克隆或复制**此仓库：

   ```bash
   git clone https://github.com/<your-username>/notes-skill.git
   ```

2. **在 Claude Code（或你的 AI agent 平台）中注册 skill。**

   > ⚠️ **重要：** 仅在 `~/.claude/skills/` 中创建 symlink **不够**。Skill 必须通过 Claude Code 的插件系统注册。裸 symlink 会显示为 "Unknown" 且无法被调用。

   **Claude Code：**
   
   在 Claude Code 中运行以下 slash command 安装 skill：
   
   ```
   /plugin install /path/to/notes-skill
   ```
   
   这会在插件系统中注册 `notes-skill` 并创建正确的 symlink。安装后可在 skill 列表中看到 `notes-skill` 名称（而非 "Unknown"）即为成功。

   **其他平台：** 按照对应平台的文档将 `SKILL.md` 注册为自定义 skill。

3. **首次运行**——skill 会自动检测尚未配置并进入 setup 模式：

   ```bash
   python scripts/setup.py --discover    # 扫描系统中的 Obsidian 笔记库
   python scripts/setup.py --path ~/Documents/Obsidian  # 直接指定笔记库路径
   ```

4. **完成。** 之后每次实质性 agent 任务结束后，skill 会自动提取知识并写入笔记库。

## 工作原理

### 8 步流水线

```
会话完成
      │
      ▼
Step 1: 生成会话摘要（AI 驱动）
      │
      ├─ Step 2: 更新日记（追加行到 ## Sessions 表格）
      ├─ Step 3: 更新项目笔记（前置到 ## Changelog）
      ├─ Step 4: 提取技术 → 创建/更新 Knowledge 节点 ── parse_session.py
      ├─ Step 5: 提取问答 → 会话日志 + Knowledge 节点踩坑记录 ── parse_session.py
      ├─ Step 6: 自动生成 Wiki 链接（Daily/, Projects/, Knowledge/）
      ├─ Step 7: 推断跨项目关联（技术重叠 ≥2）
      └─ Step 8: 维护 Knowledge-Graph + Projects-Index
      │
      ▼
sync.py 写入 obsidian-file 块 → 笔记库
```

### 两个脚本工具

| 脚本 | 用途 |
|------|------|
| `parse_session.py` | NLP 提取：技术栈（6 大类）、问答对（段落级匹配）、Wiki 链接生成（首次出现才链接，最长匹配优先）、会话时间（HHMM） |
| `sync.py` | 笔记库 I/O：解析 `obsidian-file` 块或 JSON，写入 Daily/Project/Knowledge/Knowledge-Graph/Projects-Index |

### 笔记库布局（5 个目录）

| 目录 | 用途 | 示例 |
|------|------|------|
| `Sessions/` | 每次 Agent 任务一条日志 | `2026-06-07-1430.md` |
| `Projects/` | 每个项目一个文件（Changelog 驱动） | `MyApp.md` |
| `Daily/` | 每日概览（表格形式 Sessions 列表） | `2026-06-07.md` |
| `Knowledge/` | 统一知识节点（概念/工具/框架/模式） | `Unix-Domain-Socket.md` |
| `Meta/` | Knowledge-Graph.md + Projects-Index.md | — |

### 写入内容

| 目标 | 文件 | 操作 |
|------|------|------|
| 日记 | `Daily/YYYY-MM-DD.md` | 追加行到 `## Sessions` 表格（时间/项目/做了什么/时长） |
| 会话日志 | `Sessions/YYYY-MM-DD-HHMM.md` | 创建完整会话详情（修改了什么/对话摘要/知识点/遗留问题/收获） |
| 项目笔记 | `Projects/{name}.md` | 前置到 `## Changelog`（含修改文件列表 + 遗留问题） |
| 知识节点 | `Knowledge/{Name}.md` | 创建或合并（踩坑记录表 + 来源会话） |
| 知识图谱 | `Meta/Knowledge-Graph.md` | 追加边（按 Source+Relation+Target 去重） |
| 项目索引 | `Meta/Projects-Index.md` | 合并项目行（更新日期 + 技术栈） |

## 目录结构

```
notes-skill/
├── SKILL.md                       # ⭐ 入口——AI 首先读取此文件（8 步 + 3 层指南）
├── LICENSE.txt                    # MIT 许可证
├── README.md
├── README.zh-CN.md                # 中文说明
│
├── config/
│   └── vault_config.json          # 由 setup.py 生成（用户专属，不进仓库）
│
├── scripts/
│   ├── __init__.py                # Python 包标记
│   ├── setup.py                   # 首次笔记库发现与初始化
│   ├── parse_session.py           # 会话 → 结构化知识 JSON
│   │                              #   模块 A: 技术栈提取
│   │                              #   模块 B: 问答对提取
│   │                              #   模块 C: Wiki 链接生成
│   └── sync.py                    # 将知识写入笔记库
│                                  #   模式 1: obsidian-file 块（设计标准）
│                                  #   模式 2: JSON 流水线（向后兼容）
│
├── references/
│   └── templates.md               # 全部 6 种笔记模板 + 技术分类规则
│                                  #   + 图谱 schema + 笔记库结构 + 命名约定
│
├── obsidian-note-framework.md     # 3 层笔记框架设计文档
├── obsidian-skill-design.md       # 8 步 skill 架构设计文档
│
└── evals/
    └── evals.json                 # 回归测试用例
```

## 使用方式

### obsidian-file 块模式（推荐）

AI 生成 `obsidian-file` 块并通过管道传给 `sync.py`：

````bash
cat << 'EOF' | python scripts/sync.py
```obsidian-file
path: Sessions/2026-06-07-1430.md
action: create
---
---
date: 2026-06-07
time: 14:30
duration: 45min
project: MyAPI
type: coding
tags: [python, docker]

# 2026-06-07 14:30 · MyAPI · 修复 Docker 构建

## 📁 项目
[[Projects/MyAPI]] · `requirements.txt`, `Dockerfile`

## ✏️ 修改了什么
### 修改
- `requirements.txt` — 添加 pydantic 依赖

## 💬 对话摘要
修复了因缺少 pydantic 导致的 Docker 构建失败。

## 🔗 涉及的知识点
| 知识点 | 关系 | 备注 |
|--------|------|------|
| [[Knowledge/Pydantic]] | 核心机制 | 构建依赖 |
```

```obsidian-file
path: Daily/2026-06-07.md
action: append
section: ## Sessions
---
| 14:30 | [[Projects/MyAPI]] | 修复 Docker 构建，添加 pydantic | 45min |
```
EOF
````

**三种操作**：`create`（文件不存在时创建）、`append`（在指定节标题下追加）、`replace-section`（替换整节内容）。

### JSON 流水线模式（向后兼容）

```bash
# 步骤 1：解析会话文本为结构化 JSON
python scripts/parse_session.py --session-text "<对话内容>" --output /tmp/parsed.json

# 步骤 2：将所有内容写入笔记库
python scripts/sync.py --input /tmp/parsed.json
```

### 试运行模式

```bash
python scripts/sync.py --input output.md --dry-run
python scripts/sync.py --input parsed.json --dry-run
```

在实际写入前预览所有变更——可安全地在任何环境中运行。

## 自动触发条件

当会话产生实质性成果时，skill 会自动触发：

- 完成 ≥3 次工具调用
- 编写、编辑或调试了代码
- 修复了 bug 或实现了功能
- 引入了新技术或新库
- 用户明确要求记录/保存

以下情况**不会**触发：简单问答、闲聊、无关紧要的文件读取。

## 手动触发

你也可以用以下短语显式触发：

- "记录一下" / "保存到 obsidian" / "更新笔记"
- "save this session" / "log this to obsidian"
- "整理到知识库" / "这次学到了什么"

## 参与贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT — 详见 [LICENSE.txt](LICENSE.txt)。
