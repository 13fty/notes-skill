# Obsidian Skill — 配置管理 & 统一 CLI 设计

**日期**: 2026-06-03  
**状态**: 设计完成，待实施  
**范围**: 配置管理系统、统一 CLI、skill.md 初始化流程

---

## 1. 设计目标

1. **首次使用友好** — 用户第一次加载 skill 时，自动引导完成 vault 路径配置
2. **Vault 失效检测** — 每次启动验证 vault 是否仍然可用，失效时引导恢复
3. **统一 CLI** — 所有运维操作用 `obsidian-skill <command>` 完成
4. **代码组织清晰** — 将当前混在一起的逻辑拆分为单一职责模块
5. **为跨智能体预留扩展** — 配置文件预留 agent 字段，目录结构不依赖 Claude

---

## 2. 配置 & 状态文件

### 2.1 路径

不再绑定 Claude 专属路径，使用智能体无关目录：

```
~/.obsidian-skill/
├── config.json      # 用户配置
└── state.json       # 运行时状态
```

### 2.2 config.json

```json
{
  "vault_path": "/Users/seth/Documents/Obsidian",
  "version": "1.0.0",
  "initialized_at": "2026-06-03T10:30:00",
  "agent": {
    "type": "claude-code",
    "version": "1.0.0"
  },
  "preferences": {
    "language": "zh",
    "auto_sync": true,
    "create_stubs": true
  },
  "extensions": {}
}
```

| 字段 | 用途 |
|------|------|
| `vault_path` | Obsidian vault 根路径 |
| `version` | 配置格式版本（用于 migrate 命令） |
| `initialized_at` | 首次初始化时间 |
| `agent` | 智能体类型 + 版本。值为 `claude-code` / `gemini-cli` / `codex` / `cursor` 等 |
| `preferences` | 用户偏好：语言、是否自动同步、是否自动创建 stub note 等 |
| `extensions` | 任意扩展字段，第三方可写入，互不冲突 |

### 2.3 state.json

运行时状态文件，不存放用户配置，仅记录运行过程产生的数据：

```json
{
  "version": "1.0.0",
  "last_sync": {
    "timestamp": "2026-06-03T15:42:00",
    "session_id": "abc123",
    "project": "obsidian-skill",
    "files_written": 3,
    "files_updated": 1
  },
  "discovered_vaults": [
    {
      "path": "/Users/seth/Documents/Obsidian",
      "name": "Obsidian",
      "last_seen": "2026-06-03T10:30:00",
      "valid": true
    },
    {
      "path": "/Users/seth/Documents/WorkVault",
      "name": "WorkVault",
      "last_seen": "2026-05-20T09:00:00",
      "valid": false
    }
  ],
  "sync_stats": {
    "total_sessions": 42,
    "total_files_written": 156,
    "total_qa_extracted": 23,
    "total_tech_entries": 87,
    "first_sync": "2025-12-01T08:00:00"
  },
  "extensions": {}
}
```

| 字段 | 用途 |
|------|------|
| `last_sync` | 最近一次同步的详情：时间、会话 ID、项目、影响文件数 |
| `discovered_vaults` | 历史扫描发现的所有 vault，含有效状态，供 repair 时快速匹配 |
| `sync_stats` | 累计统计，用于 doctor 报告和用户概览 |
| `extensions` | 预留扩展 |

---

## 3. Skill 初始化流程（skill.md Step 0）

skill.md 在现有工作流之前新增 **Step 0 — Initialize Configuration**。

```
Skill 启动
    ↓
读取 ~/.obsidian-skill/config.json
    ↓
存在？
├── 是 → 读取 vault_path
│        │
│        ↓ 执行 Vault 失效检测
│        │
│        ├── 通过 → 继续核心流程
│        └── 失败 → 提示用户 vault 已不可用
│                   ↓
│                   自动搜索系统中所有 Obsidian Vault
│                   ↓
│                   找到匹配的？
│                   ├── 是 → AskUserQuestion 确认是否更新路径
│                   │        ├── 确认 → 更新 config，继续
│                   │        └── 拒绝 → 进入重新选择流程
│                   └── 否 → 进入重新选择流程
│
└── 否 → 自动搜索 Obsidian Vault
         ↓
         找到？
         ├── 是 → AskUserQuestion 列出候选，用户选择/确认
         │
         └── 否 → AskUserQuestion 输入路径
                  ├── 成功 → 验证路径
                  └── 跳过 → 纯文本回退："请在聊天中回复你的 Vault 路径"
         ↓
         验证 → 写入 config → 继续核心流程
```

### 3.1 Vault 搜索策略

| 平台 | 搜索路径 |
|------|---------|
| macOS | `~/Documents`, `~/Library/Mobile Documents/iCloud~md~obsidian`, `~/Library/Application Support/obsidian` |
| Linux | `~/Documents`, `~/*/Obsidian` |
| Windows | `%USERPROFILE%\Documents`, `%APPDATA%\Obsidian` |

搜索特征：目录下存在 `.obsidian` 子目录。

### 3.2 Vault 有效性验证

```python
def validate_vault(path: str) -> dict:
    checks = {
        "path_exists": False,           # [必须] 路径存在
        "is_directory": False,          # [必须] 是目录
        "dot_obsidian_exists": False,   # [必须] .obsidian 子目录存在
        "readable": False,              # [必须] 可读
        "writable": False,              # [必须] 可写
        "obsidian_json_exists": False,  # [可选] .obsidian/obsidian.json 存在
        "has_markdown": False,          # [可选] 至少有一个 .md 文件
    }
```

**必须项** 任一失败 → vault 不可用，阻止继续。  
**可选项** 缺失 → 仅记录 warning，不阻止。

---

## 4. 统一 CLI

### 4.1 入口

```
obsidian-skill <command> [options]
```

单一入口 `scripts/cli.py`，内部路由到各模块。

### 4.2 命令一览

| 命令 | 功能 | 对应模块 |
|------|------|---------|
| `init` | 首次初始化向导：搜索 → 选择 → 验证 → 写入 config | `lib/vault.py` + `lib/config.py` |
| `config` | 查看/修改配置：`get <key>`, `set <key> <value>`, `list`, `reset` | `lib/config.py` |
| `validate` | 验证 vault 有效性，输出结构化报告（JSON / 可读文本） | `lib/vault.py` |
| `search` | 搜索系统中所有 Obsidian vault，列出候选 | `lib/vault.py` |
| `repair` | 原 vault 失效时尝试自动找回并更新 config | `lib/vault.py` |
| `sync` | 将 AI 对话内容同步到 vault（当前 sync.py 的逻辑） | `lib/sync.py` |
| `migrate` | 配置格式版本升级 / 跨 agent 迁移 | `lib/config.py` |
| `doctor` | 全量诊断：检查 config / vault / 模板 / 权限，输出报告 | 综合 |

### 4.3 使用示例

```bash
# 首次安装
obsidian-skill init

# 交互式选择
obsidian-skill init --interactive

# 直接指定路径
obsidian-skill init --vault /path/to/vault

# 查看当前配置
obsidian-skill config list

# 修改偏好
obsidian-skill config set preferences.language en

# 验证 vault
obsidian-skill validate
# → {"valid": true, "checks": {...}, "warnings": []}

# 诊断
obsidian-skill doctor
```

---

## 5. 目录结构

```
obsidian-second-brain/
│
├── skill.md                      # 核心 skill 指令（Claude 读取），新增 Step 0
│
├── scripts/
│   └── cli.py                    # 统一 CLI 入口，click/argparse 路由
│
├── lib/
│   ├── __init__.py
│   ├── config.py                 # 配置读写、迁移（~/.claude/obsidian-skill.json）
│   ├── vault.py                  # Vault 搜索、验证、修复
│   ├── sync.py                   # 同步核心逻辑（从当前 sync.py 提取）
│   ├── parser.py                 # 解析逻辑（从当前 parse_session.py 提取）
│   └── templates.py              # 模板渲染（从当前 templates.md 提取）
│
├── templates/
│   ├── daily.md
│   ├── project.md
│   └── knowledge.md
│
├── README.md
│
└── .gitignore
```

### 5.1 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| `cli.py` | CLI 路由，参数解析，调用 lib 模块 | 所有 lib 模块 |
| `config.py` | 配置 CRUD、格式版本迁移、状态文件读写 | 无 |
| `vault.py` | 跨平台 vault 搜索、多层验证、修复、discovered_vaults 更新 | config.py |
| `sync.py` | 解析 AI 输出 → 写入 vault 文件 | vault.py, templates.py |
| `parser.py` | 从对话文本提取技术栈/QA/链接（纯文本处理） | 无 |
| `templates.py` | 模板渲染（变量替换、根据偏好生成） | config.py |

---

## 6. 跨智能体预留

当前仅实现 Claude Code，但结构预留了扩展点：

1. `config.agent.type` — 标记当前智能体类型，未来值为 `claude-code` / `gemini-cli` / `codex` / `cursor`
2. `skill.md` — 核心逻辑保持智能体无关。需要不同智能体的特定指令时，可新增 `agents/claude-code.md` / `agents/gemini-cli.md` 作为轻量适配层
3. `lib/` 下的 Python 模块与智能体无关，所有智能体共享同步逻辑
4. CLI 命令 `migrate` 预留了跨 agent 迁移能力

---

## 7. 实施步骤

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 1 | 创建目录结构 + `.gitignore` | 全部新建 |
| 2 | 实现 `lib/config.py` | config.py |
| 3 | 实现 `lib/vault.py`（搜索 + 验证 + 修复） | vault.py |
| 4 | 从现有代码提取 `lib/sync.py` | sync.py, 现有 sync.py |
| 5 | 从现有代码提取 `lib/parser.py` | parser.py, 现有 parse_session.py |
| 6 | 从现有代码提取 `lib/templates.py` | templates.py, 现有 templates.md |
| 7 | 实现 `scripts/cli.py` 统一入口 | cli.py |
| 8 | 更新 `skill.md` 新增 Step 0 | skill.md |
| 9 | 更新 `templates/` 拆分模板文件 | templates/ |
| 10 | 更新 `README.md` | README.md |

---

## 8. 设计决策记录

- **配置放 `~/.obsidian-skill/` 而非 `~/.claude/`** — 智能体无关路径，利于未来支持 Gemini CLI、Codex、Hermes 等
- **`.obsidian` 是唯一必须标记** — `obsidian.json` 不是所有版本都有，不能作为硬性检查
- **统一 CLI > 分散脚本** — 降低认知成本，符合成熟工具惯例
- **`lib/` 单一职责拆分** — 当前 `sync.py` 同时包含解析、模板、写入，拆为独立模块便于测试和复用
