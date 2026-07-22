# Pi Agent 会话操作速查笔记

> 会话默认保存在 `~/.pi/agent/sessions/`，按**工作目录（cwd）**组织，每个会话是一个 **JSONL** 文件，内部为树结构（可分支）。
> 配置目录可用环境变量 `PI_CODING_AGENT_DIR` 覆盖；会话存储目录可用 `PI_CODING_AGENT_SESSION_DIR` 或 `--session-dir` 覆盖。

## 一、核心概念

- **会话（Session）**：一次对话，自动保存，可继续、分支、回看历史路径。
- **树结构**：每条记录有 `id` 和 `parentId`，当前位置是"活动叶子（active leaf）"。可在任意历史节点继续，形成分支。
- **命名会话**：用 `/name` 或 `--name` 起名后，在列表中更易查找。

## 二、命令行会话选项

| 选项 | 说明 |
|------|------|
| `-c`, `--continue` | 继续**最近**一次会话（不列出全部） |
| `-r`, `--resume` | 启动即打开**历史会话选择器** |
| `--session <path\|id>` | 用指定会话文件或（部分）UUID 打开 |
| `--fork <path\|id>` | 从指定会话派生新会话（可指定分支点） |
| `--session-dir <dir>` | 自定义会话存储目录 |
| `--no-session` | 临时模式，不保存会话 |
| `--name <name>`, `-n <name>` | 启动时设置会话显示名 |

示例：
```bash
pi -c                                   # 继续最近会话
pi -r                                   # 浏览历史会话
pi --name "release audit" -p "审查本仓库"
pi --session ~/.pi/agent/sessions/xxx.jsonl
pi --fork <path|id>                     # 从历史派生成新会话
```

## 三、交互模式会话命令（斜杠命令）

在编辑器输入 `/` 调出命令补全，会话相关如下：

| 命令 | 说明 |
|------|------|
| `/resume` | 浏览并选择**过去会话**（打开选择器） |
| `/new` | 开始**新会话** |
| `/name <name>` | 设置当前会话显示名 |
| `/session` | 显示**当前**会话信息（文件、ID、消息数、tokens、费用） |
| `/tree` | 浏览当前会话树，跳到任意历史节点继续 |
| `/fork` | 从更早的**用户消息**新建一个会话文件 |
| `/clone` | 把当前活动分支**复制**成新会话文件 |
| `/compact [prompt]` | 手动压缩上下文（可带自定义指令） |
| `/export [file]` | 导出会话为 HTML 或 JSONL |
| `/import <file>` | 从 JSONL 导入并恢复会话 |
| `/share` | 上传为私有 GitHub gist，生成可分享 HTML 链接 |

> 注意：`/session` 只显示**当前**会话的详情，不是列表；要看列表请用 `/resume` 或 `pi -r`。

## 四、历史会话选择器（/resume 与 pi -r 共用）

在 picker 中可以：

| 操作 | 按键 |
|------|------|
| 搜索 | 直接输入 |
| 切换路径显示 | `Ctrl+P` |
| 切换排序模式 | `Ctrl+S` |
| 仅显示已命名会话 | `Ctrl+N` |
| 重命名 | `Ctrl+R` |
| 删除（需确认） | `Ctrl+D` |

> 删除优先使用系统 `trash` CLI 软删除；无 `trash` 时才会永久删除文件。

## 五、会话命名

```text
/name Refactor auth module
```
或启动时：
```bash
pi --name "Refactor auth module"
pi --name "CI audit" -p "审查构建失败"
```
命名后能在 `/resume` 和 `pi -r` 中更易检索。

## 六、分支：/tree、/fork、/clone 对比

| 特性 | `/tree` | `/fork` | `/clone` |
|------|---------|---------|----------|
| 输出 | 同一会话文件 | 新会话文件 | 新会话文件 |
| 视图 | 完整树 | 仅用户消息选择器 | 当前活动分支 |
| 典型用途 | 就地探索替代方案 | 从较早提示开启新会话 | 继续前复制当前成果 |
| 分支摘要 | 可选 | 无 | 无 |

### /tree 导航键

| 按键 | 动作 |
|------|------|
| ↑/↓ | 上下移动 |
| ←/→ | 上下翻页 |
| `Ctrl+←`/`Ctrl+→` 或 `Alt+←`/`Alt+→` | 折叠/展开 或 跨分支段跳转 |
| `Shift+L` | 给选中项设置/清除标签 |
| `Shift+T` | 切换标签时间戳 |
| `Enter` | 选择该节点 |
| `Escape` / `Ctrl+C` | 取消 |
| `Ctrl+O` | 切换过滤模式 |

**过滤模式**：default、no-tools、user-only、labeled-only、all（可用 `treeFilterMode` 在设置中配置默认）。

**选择行为**：
- 选用户/自定义消息 → 叶子移到该消息的父节点，文本放入编辑器，可编辑后重发形成新分支。
- 选助手/工具/压缩等非用户条目 → 叶子移到该节点，编辑器清空，从该点继续。
- 选根用户消息 → 叶子重置为空白对话，原始提示放入编辑器。

## 七、分支摘要（Branch Summaries）

当 `/tree` 从一条分支切到另一条时，Pi 可总结被放弃的分支并附到新位置，保留上下文而不重放整条分支。提示选项：
1. 不摘要
2. 用默认提示摘要
3. 用自定义关注点指令摘要

## 八、查看会话详情

- `/session`：显示当前会话文件、ID、消息数、tokens、费用。
- 文件格式与 `SessionManager` API 见 `session-format.md`。

## 九、导出与分享

- `/export [file]`：导出为 HTML（或 JSONL）。
- `/share`：上传私有 GitHub gist，得可分享 HTML 链接。
- CLI：`pi --export <in> [out]` 将会话导出为 HTML。

## 十、删除会话

- 在 `/resume` 或 `pi -r` 选择器里 `Ctrl+D` 然后确认。
- 优先走 `trash` 软删除。

## 十一、常用组合示例

```bash
# 继续最近会话
pi -c

# 启动选历史
pi -r

# 命名的一次性会话
pi --name "release audit" -p "审计本仓库"

# 从历史会话派生
pi --fork <path|id>

# 指定目录存储
pi --session-dir /custom/sessions -r
```
