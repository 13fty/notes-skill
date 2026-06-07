# Obsidian 笔记框架设计文档

> 目标：每次使用 Agent 修改项目后，都能在 Obsidian 里清楚看到 **什么时间、对哪个项目、改了什么、涉及哪些知识点**。

---

## 一、三层结构总览

```
层级          文件位置                        核心问题
─────────────────────────────────────────────────────────────
① 会话层     Sessions/YYYY-MM-DD-HHMM.md    这次 Agent 做了什么？
② 项目层     Projects/{项目名}.md            这个项目的全部历史？
             Daily/YYYY-MM-DD.md            今天做了哪些事？
③ 知识层     Knowledge/{概念名}.md           这个知识点是什么？
```

**信息流向：**
- 每次 Agent 会话 → 生成一条 Session Log
- Session Log → 向上更新 Project Note 的 Changelog
- Session Log → 向上更新 Daily Note 的 Sessions 列表
- Session Log → 向下链接涉及的 Knowledge 节点
- Knowledge 节点之间 → 互相链接（父子概念、相关概念）

---

## 二、Vault 目录结构

```
MyVault/
│
├── Sessions/                    ← 会话记录（主入口）
│   ├── 2026-06-07-1430.md
│   └── 2026-06-07-0915.md
│
├── Projects/                    ← 项目笔记（每个项目一个文件）
│   ├── AgentWatch.md
│   ├── wxbot.md
│   └── FingerCounter.md
│
├── Daily/                       ← 日记（按天聚合）
│   ├── 2026-06-07.md
│   └── 2026-06-06.md
│
├── Knowledge/                   ← 知识节点（概念原子）
│   ├── Unix-Domain-Socket.md
│   ├── PTY.md
│   ├── IPC.md
│   └── SwiftUI.md
│
└── Meta/                        ← 元数据索引（可选）
    ├── Knowledge-Graph.md       ← 所有知识节点关系表
    └── Projects-Index.md        ← 项目总览
```

---

## 三、Session Log 模板（最重要的文件）

**文件路径：** `Sessions/YYYY-MM-DD-HHMM.md`  
**命名示例：** `Sessions/2026-06-07-1430.md`

```markdown
---
date: 2026-06-07
time: 14:30
duration: 52min
project: AgentWatch
type: coding          # coding | debugging | learning | design
tags: [ipc, swift, socket]
---

# 2026-06-07 14:30 · AgentWatch · IPC 架构重构

## 📁 项目
[[Projects/AgentWatch]] · `src/socket.py`, `src/handler.py`

## ✏️ 修改了什么

### 新增
- `socket.py` — 实现 Unix Domain Socket 服务端监听逻辑
- `handler.py` — 添加 `on_message()` 分发函数，处理 JSON 协议帧

### 修改
- `main.swift` — 将硬编码路径改为从 `Config.socketPath` 读取
- `AppDelegate.swift` — 添加 socket 断开重连逻辑

### 删除
- `legacy_pipe.py` — 旧版 named pipe 方案已废弃

## 💬 对话摘要

用 Unix Domain Socket 替换了原来的 named pipe 方案。主要原因是
named pipe 在进程退出后需要手动清理，而 UDS 可以绑定到 `/tmp` 
下的临时路径，Swift 端和 Python 端各持一个 fd，通过 JSON 帧通信。

调试过程中发现 Swift 端的 `recv()` 会阻塞主线程，改用 
`DispatchQueue.global()` 后解决。

## 🔗 涉及的知识点

| 知识点 | 关系 | 备注 |
|--------|------|------|
| [[Knowledge/Unix-Domain-Socket]] | 核心机制 | 本次新学 |
| [[Knowledge/IPC]] | 父概念 | 进程间通信总览 |
| [[Knowledge/PTY]] | 相关 | AgentWatch 同时用到 |
| [[Knowledge/DispatchQueue]] | 相关 | Swift 并发处理 |

## ❓ 遗留问题

- [ ] PTY 进程崩溃后，socket 文件没有清理 — 待查
- [ ] Swift 端重连间隔目前写死 3s，后续改为指数退避

## ✅ 本次收获

- Unix Domain Socket 比 named pipe 更适合同机进程通信
- Swift 的 `recv()` 默认阻塞，需要放到后台队列
```

---

## 四、Project Note 模板

**文件路径：** `Projects/{项目名}.md`

```markdown
---
status: active           # active | paused | completed
created: 2026-05-10
updated: 2026-06-07
tech: [Swift, SwiftUI, Python, UDS]
tags: [project, macos, ai-tools]
---

# AgentWatch

## Overview

macOS 菜单栏工具，用于监控 AI Agent CLI 工具（Claude Code、Codex CLI 等）的
运行状态。Swift/SwiftUI 前端 + Python PTY 后端，通过 Unix Domain Socket 通信。

## Tech Stack

| 类别 | 技术 |
|------|------|
| 语言 | Swift · Python |
| 框架 | SwiftUI · AppKit |
| 通信 | Unix Domain Socket · PTY |
| 工具 | Xcode · pip |

## Changelog

<!-- 最新在前，由 Agent 会话自动追加 -->

### 2026-06-07 · IPC 架构重构
> [[Sessions/2026-06-07-1430]] · 52min

将 named pipe 替换为 Unix Domain Socket。Swift 端改用 
`DispatchQueue.global()` 处理阻塞 `recv()`，添加断开重连逻辑。

**修改文件：** `socket.py` `handler.py` `main.swift` `AppDelegate.swift`  
**遗留：** PTY 崩溃后 socket 文件未清理

---

### 2026-06-01 · 菜单栏 UI 优化
> [[Sessions/2026-06-01-1015]] · 35min

重新设计菜单栏图标状态（idle / running / error），添加 popover 显示
Agent 输出的最后 5 行。

**修改文件：** `MenuBarView.swift` `StatusIcon.swift`

## Open Issues

- [ ] PTY 进程崩溃后 socket 文件未清理
- [ ] 重连间隔写死 3s，需改为指数退避
- [ ] 菜单栏 popover 在 macOS 13 以下有布局 bug

## Related Sessions

<!-- 该项目的所有会话，按时间倒序 -->
- [[Sessions/2026-06-07-1430]] · IPC 架构重构
- [[Sessions/2026-06-01-1015]] · 菜单栏 UI 优化
- [[Sessions/2026-05-28-2100]] · PTY 包装层初版

## Knowledge Nodes

<!-- 该项目涉及的所有知识点 -->
[[Knowledge/Unix-Domain-Socket]] · [[Knowledge/PTY]] · 
[[Knowledge/IPC]] · [[Knowledge/SwiftUI]] · [[Knowledge/DispatchQueue]]
```

---

## 五、Daily Note 模板

**文件路径：** `Daily/YYYY-MM-DD.md`

```markdown
---
date: 2026-06-07
tags: [daily]
---

# 2026-06-07 周日

## Sessions

<!-- 当天所有 Agent 会话，按时间顺序 -->

| 时间 | 项目 | 做了什么 | 时长 |
|------|------|----------|------|
| 09:15 | [[Projects/AgentWatch]] | Qt CMake 初始化配置 | 40min |
| 14:30 | [[Projects/AgentWatch]] | IPC 架构重构 | 52min |

## Wins Today

- Unix Domain Socket 双向通信跑通 ✓
- 理解了 Swift DispatchQueue 的阻塞模型

## Blockers

- PTY 崩溃后文件残留问题还没定位

## Notes

今天主要在搞 AgentWatch 的 IPC 部分，比预期花了更多时间在
Swift 端的线程问题上。明天继续查 PTY 崩溃的原因。
```

---

## 六、Knowledge Node 模板

**文件路径：** `Knowledge/{概念名}.md`  
**命名规则：** 用连字符，如 `Unix-Domain-Socket.md`

```markdown
---
type: concept           # concept | tool | framework | pattern
tags: [ipc, linux, networking]
first_seen: 2026-06-07
---

# Unix Domain Socket

## 一句话

同一台机器上进程间通信（IPC）的套接字机制，通过文件系统路径寻址，
比 TCP loopback 延迟更低、开销更小。

## 核心机制

- 绑定到文件系统路径（如 `/tmp/agentwatch.sock`）
- 服务端 `bind()` → `listen()` → `accept()`
- 客户端 `connect()` → `send()` / `recv()`
- 进程退出后需手动删除 socket 文件，否则下次 bind 报错

## 代码片段

```python
# Python 服务端
import socket, os

SOCK_PATH = "/tmp/agentwatch.sock"
if os.path.exists(SOCK_PATH):
    os.remove(SOCK_PATH)

srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
srv.bind(SOCK_PATH)
srv.listen(1)
conn, _ = srv.accept()
data = conn.recv(1024)
```

## 与其他概念的关系

- 父概念：[[Knowledge/IPC]]
- 同类机制：[[Knowledge/Named-Pipe]]（named pipe，同机但只支持单向）
- 对比：TCP loopback 走网络协议栈，UDS 直接走内核缓冲区，延迟约低 30%
- 在项目中使用：[[Projects/AgentWatch]]

## 踩坑记录

| 日期 | 问题 | 解决方式 |
|------|------|----------|
| 2026-06-07 | Swift `recv()` 阻塞主线程 | 改用 `DispatchQueue.global()` |
| 2026-06-07 | 进程崩溃后 `.sock` 文件残留 | 启动时检查并删除旧文件 |

## 来源会话

[[Sessions/2026-06-07-1430]]
```

---

## 七、快速查找路径

用 Obsidian 的 **Graph View** 打开时，三层结构自然呈现：

```
想知道…                          打开…
─────────────────────────────────────────────────────────────
某天做了什么                     Daily/YYYY-MM-DD.md
某个项目改了什么（全史）           Projects/{项目名}.md
某次 Agent 对话的细节             Sessions/YYYY-MM-DD-HHMM.md
某个知识点是什么 / 在哪用过        Knowledge/{概念名}.md
两个知识点的关系                  从任一 Knowledge 节点的"与其他概念"
某知识点被哪些项目用过             Knowledge 节点底部的"在项目中使用"
```

---

## 八、Agent 每次会话后需要填写的最小集合

如果每次都写全部内容太麻烦，至少填这五项：

```markdown
## 项目
[[Projects/xxx]]

## 修改了什么
- 文件名 — 做了什么

## 对话摘要
（2-3 句话）

## 涉及的知识点
[[Knowledge/xxx]] [[Knowledge/yyy]]

## 遗留问题
- [ ] xxx
```

其他字段（对话摘要详情、收获、踩坑）可以之后补充，也可以让 Agent 自动生成。

---

## 九、命名约定

| 类型 | 格式 | 示例 |
|------|------|------|
| Session | `YYYY-MM-DD-HHMM` | `2026-06-07-1430` |
| Project | PascalCase | `AgentWatch`, `FingerCounter` |
| Daily | `YYYY-MM-DD` | `2026-06-07` |
| Knowledge | Kebab-case | `Unix-Domain-Socket`, `PTY` |

---

*框架版本 v1.0 · 根据 Lefty 的实际项目场景（AgentWatch / wxbot / Qt CMake 等）设计*
