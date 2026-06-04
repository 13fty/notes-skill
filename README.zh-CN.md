# Notes-Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org/)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen.svg)](https://github.com)

> 📖 [English version](README.md)

一个 AI agent 技能，可在每次 agent 任务完成后自动 hook，将结构化知识同步到 [Obsidian](https://obsidian.md) 笔记库中。与手动触发的笔记工具不同，本系统在完成实质性的编码、调试或设计会话后**自动触发**——提取学到的内容并持久化，无需用户手动操作。

## 设计理念

- **自动触发**：agent 任务完成后自动运行，不依赖用户手动请求
- **仅追加写入**：绝不删除或覆盖用户已有内容
- **结构化提取**：将零散的对话转化为类型化的知识（技术栈、变更记录、问答、图谱边）
- **跨项目感知**：自动推断项目之间的关联关系
- **持续增长**：知识图谱边随时间累积；用得越久，信息越丰富

## 快速开始

### 环境要求

- Python 3.9+（仅依赖标准库，无需 pip 安装任何包）
- 一个包含 `.obsidian` 目录的 [Obsidian](https://obsidian.md) 笔记库
- 对笔记库路径有写入权限

### 安装

1. **克隆或复制**此仓库到你的 skill 目录：

   ```bash
   git clone https://github.com/<your-username>/notes-skill.git
   ```

2. **注册** `SKILL.md` 为你 AI agent 平台的自定义 skill。

3. **首次运行**——skill 会自动检测尚未配置并进入 setup 模式：

   ```bash
   python scripts/setup.py --discover    # 扫描系统中的 Obsidian 笔记库
   python scripts/setup.py --path ~/Documents/Obsidian  # 直接指定笔记库路径
   ```

4. **完成。** 之后每次实质性 agent 任务结束后，skill 会自动提取知识并写入笔记库。

## 工作原理

### 流水线

```
会话完成
      │
      ▼
config/vault_config.json 存在？ ──否──> SETUP 模式: scripts/setup.py
      │
     是
      │
      ▼
extract.py ──> extracted.json
      │
      ▼
write_vault.py ──> 日记、项目笔记、技术栈索引、问答归档
      │
      ▼
graph_update.py ──> 知识图谱边、节点注册表、跨项目关联
```

### 写入内容

| 目标 | 文件 | 操作 |
|--------|------|-----------|
| 日记 | `Daily/YYYY-MM-DD.md` | 追加到 `## AI Sessions` |
| 项目笔记 | `Projects/{name}.md` | 前置插入 `## Session Log`，合并 `## Tech Stack` |
| 技术栈索引 | `Meta/Tech Stack Index.md` | 合并条目（去重） |
| 问答归档 | `Meta/QA Archive.md` | 追加问题-解决方案对 |
| 知识图谱 | `Meta/Knowledge Graph.md` | 追加边（按三元组去重） |
| 节点注册表 | `Meta/Nodes.md` | 合并节点条目 |

## 目录结构

```
notes-skill/
├── SKILL.md                       # ⭐ 入口——AI 首先读取此文件
├── LICENSE.txt                    # MIT 许可证
├── README.md
├── README.zh-CN.md                # 中文说明
│
├── config/
│   └── vault_config.json          # 由 setup.py 生成（用户专属，不进仓库）
│
├── scripts/
│   ├── __init__.py                # Python 包标记
│   ├── setup.py                   # 首次 setup 向导
│   ├── extract.py                 # 会话 → 结构化知识 JSON
│   ├── write_vault.py             # 写入/追加笔记到笔记库
│   └── graph_update.py            # 更新知识图谱边
│
├── references/
│   ├── note_templates.md          # 所有笔记类型的 Markdown 模板
│   ├── extract_rules.md           # 分类规则、信号词
│   ├── graph_schema.md            # 节点/边类型定义
│   └── vault_structure.md         # 推荐的笔记库目录规范
│
├── agents/
│   └── knowledge_extractor.md     # 用于复杂会话提取的子 agent
│
└── evals/
    └── evals.json                 # 回归测试用例
```

## 使用方式

### 手动运行流水线

```bash
# 步骤 1：从对话中提取结构化知识
python scripts/extract.py --session-text "<对话内容>" --output /tmp/extracted.json

# 步骤 2：将笔记写入笔记库（日记、项目笔记、技术栈索引、问答归档）
python scripts/write_vault.py --input /tmp/extracted.json

# 步骤 3：更新知识图谱边和节点注册表
python scripts/graph_update.py --input /tmp/extracted.json
```

### 试运行模式

所有写入脚本均支持 `--dry-run`，可预览变更而不实际写入：

```bash
python scripts/write_vault.py --input extracted.json --dry-run
python scripts/graph_update.py --input extracted.json --dry-run
```

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
