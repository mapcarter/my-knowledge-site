# Pi Agent 工具操作速查笔记

> 本文汇总 Pi Agent 中与"工具（Tools）"相关的全部操作：内置工具、命令行控制、工具调度机制、运行时管理、自定义工具开发、工具事件拦截与渲染。可作为日常查阅的操作指南。
> 与 `pi-sessions-cheatsheet.md` 配套使用。

---

## 一、内置工具清单

Pi 自带的 6 个内置工具（`usage.md`）：

| 工具 | 作用 |
|------|------|
| `read` | 读取文件内容（支持文本与图片） |
| `bash` | 执行 shell 命令 |
| `edit` | 精确文本替换式编辑文件（支持多处 `edits`） |
| `write` | 创建/覆盖写入文件 |
| `grep` | 内容搜索 |
| `find` | 文件查找 |

> 工具调用默认**并行执行**（见第六节）。`bash`/`read` 等返回的大体积是上下文的主要消耗来源（不是工具数量本身）。

---

## 二、命令行工具选项

启动 Pi 时限定可用工具集（`usage.md` 的 Tool Options）：

| 选项 | 说明 |
|------|------|
| `--tools <list>`, `-t <list>` | **白名单**：只允许指定工具（内置+扩展+自定义） |
| `--exclude-tools <list>`, `-xt <list>` | 禁用指定工具，其余保留 |
| `--no-builtin-tools`, `-nbt` | 关闭内置工具，但保留扩展/自定义工具 |
| `--no-tools`, `-nt` | 禁用全部工具 |

示例：
```bash
# 只读审查模式
pi --tools read,grep,find,ls -p "审查代码"

# 保留全部，仅关掉某个交互式工具
pi --exclude-tools ask_question

# 完全无工具（纯对话）
pi --no-tools -p "解释这段需求"
```

---

## 三、工具调度机制（谁决定用哪个）

- **具体用哪个、何时用、调几次、是否并行 —— 由大模型自己决定。**
  工具注册后"出现在系统提示里"，模型读到 `promptSnippet` 描述后自主调用，属于标准 tool-use 流程。
- **用户/扩展只控制"工具池的范围"（哪些工具可见/可用），以及通过提示"引导"偏好，但不强制逐任务指定。**

控制工具池的三种手段：
1. 运行时 `pi.setActiveTools([...])`（见第四节）
2. 启动时 CLI 白/黑名单（见第二节）
3. 软引导：`AGENTS.md`/`CLAUDE.md`、`promptGuidelines`、skills 影响模型选择倾向

---

## 四、运行时查看与管理活跃工具（扩展 API）

`extensions.md` 提供三个 API 管理 active tools（对内置工具和动态注册工具均有效）：

```typescript
const active = pi.getActiveTools();   // 当前激活的工具名 string[]
const all = pi.getAllTools();         // 所有已配置工具的元数据
pi.setActiveTools([...new Set([...active, "my_tool"])]); // 保留现有 + 启用新工具
pi.setActiveTools(["read", "bash"]);  // 切换到只读集
```

`pi.getAllTools()` 返回字段：`name`、`description`、`parameters`、`promptGuidelines`、`sourceInfo`。
常见 `sourceInfo.source` 值：
- `builtin` —— 内置工具
- `sdk` —— 通过 `createAgentSession({ customTools })` 传入
- 扩展源元数据 —— 扩展注册的工具

> `registerTool()` 在扩展加载后、启动后、`session_start`/命令/事件处理器内都可调用，新工具即时刷新，无需 `/reload`。

---

## 五、自定义工具开发（registerTool）

通过 `pi.registerTool(definition)` 注册模型可调用工具（`extensions.md` 的 Custom Tools 章节）。

### 字段说明

| 字段 | 说明 |
|------|------|
| `name` | 工具名（唯一标识） |
| `label` | 显示名（TUI 渲染用） |
| `description` | 工具描述（展示给 LLM） |
| `promptSnippet` | 一句话描述，进入系统提示 `Available tools` 区；省略则不进该区 |
| `promptGuidelines` | 工具专属指引，仅当工具**激活**时追加到 `Guidelines` 区 |
| `parameters` | 参数 schema（用 `typebox` 的 `Type.*`） |
| `prepareArguments(args)` | 可选；schema 校验前运行，用于兼容旧会话参数形状 |
| `execute(...)` | 实际执行逻辑 |
| `renderCall` / `renderResult` | 可选；自定义 TUI 渲染 |

`promptGuidelines` 注意事项：
- 平铺追加到 `Guidelines`，**无工具名前缀**，每条必须自报工具名。
- 写 `Use my_tool when...`，不要写 `Use this tool when...`（模型无法分辨"this"指谁）。

### 参数 schema 要点
- 字符串枚举用 `StringEnum`（来自 `@earendil-works/pi-ai`），因为 `Type.Union`/`Type.Literal` 与 Google API 不兼容。
- `@` 前缀路径：部分模型会把 `@` 带进路径参数。内置工具会先剥离前导 `@`；自定义工具接受路径时也应自行归一化。

### 最小示例

```typescript
import { Type } from "typebox";
import { StringEnum } from "@earendil-works/pi-ai";

pi.registerTool({
  name: "my_tool",
  label: "My Tool",
  description: "What this tool does",
  promptSnippet: "List or add items in the project todo list",
  promptGuidelines: [
    "Use my_tool for todo planning instead of direct file edits when the user asks for a task list.",
  ],
  parameters: Type.Object({
    action: StringEnum(["list", "add"] as const),
    text: Type.Optional(Type.String()),
  }),
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    if (signal?.aborted) return { content: [{ type: "text", text: "Cancelled" }] };
    onUpdate?.({ content: [{ type: "text", text: "Working..." }] });
    return { content: [{ type: "text", text: "Done" }], details: {} };
  },
});
```

---

## 六、工具执行特性

### 1. 默认并行执行
同一助手消息的同级工具调用先顺序预检（preflight），再并发执行。因此 `tool_call` 处理器**不保证**能看到同批兄弟工具的结果（`extensions.md`）。

### 2. 文件变更队列（withFileMutationQueue）
若自定义工具改文件，必须用 `withFileMutationQueue()` 接入与内置 `edit`/`write` 相同的按文件队列，否则并发读写可能相互覆盖。
- 传**真实目标文件路径**（先 `resolve` 成绝对路径）。
- 已有文件经 `realpath()` 规范化，同一文件的符号链接别名共享一个队列。
- 必须包裹整个"读-改-写"窗口，而非仅最终写入。

```typescript
import { withFileMutationQueue } from "@earendil-works/pi-coding-agent";

async execute(_id, params, _signal, _onUpdate, ctx) {
  const absolutePath = resolve(ctx.cwd, params.path);
  return withFileMutationQueue(absolutePath, async () => {
    const current = await readFile(absolutePath, "utf8");
    const next = current.replace(params.oldText, params.newText);
    await writeFile(absolutePath, next, "utf8");
    return { content: [{ type: "text", text: `Updated ${params.path}` }], details: {} };
  });
}
```

### 3. 错误信号
从 `execute()` **抛错** → 结果标记 `isError: true` 并报告给模型。仅 `return` 无论返回什么属性都**不会**置错误标志。

### 4. 早期终止（terminate）
`execute()` 返回 `terminate: true` 提示：当前工具批次执行完后跳过自动的下一次 LLM 调用。仅当该批次**所有**最终工具结果都返回 `terminate: true` 才生效（适合结构化输出终态）。

### 5. 参数兼容（prepareArguments）
`prepareArguments(args)` 在 schema 校验与 `execute()` 之前运行，用于兼容旧会话中参数形状已变更的情况（例如 `edit` 从顶层 `oldText/newText` 改为 `edits: [...]`）。保持公开 schema 严格，不要把废弃兼容字段塞进 `parameters`。

---

## 七、工具渲染（自定义 UI）

`registerTool` 可传 `renderCall(args, theme, context)` 与 `renderResult(result, options, theme, context)` 控制工具调用/结果在 TUI 中的显示，而不影响发送给 LLM 的内容（`content`）与用于状态/重建的 `details`。

---

## 八、工具事件（拦截 / 修改 / 监控）

扩展可订阅工具相关事件（`extensions.md` Events 章节）：

| 事件 | 触发时机 | 能力 |
|------|----------|------|
| `tool_execution_start` | 工具开始执行前 | 监控 |
| `tool_execution_update` | 执行进度更新 | 监控 |
| `tool_execution_end` | 执行结束 | 监控 |
| `tool_call` | 在 `tool_execution_start` 之后、工具执行前 | **可拦截/修改/阻塞** |
| `tool_result` | 工具结果产生后 | 中间件式修改（可链式） |

### tool_call（可阻塞，最常用）
- `event.toolName`、`event.toolCallId`、`event.input`（**可变**）。
- 就地修改 `event.input` 可修补工具参数，影响实际执行；后续 handler 可见前序修改；修改后**不再重新校验**。
- 返回 `{ block: true, reason?: string }` 可阻止该工具调用。

```typescript
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

pi.on("tool_call", async (event, ctx) => {
  if (isToolCallEventType("bash", event)) {
    event.input.command = `source ~/.profile\n${event.input.command}`;
    if (event.input.command.includes("rm -rf")) {
      return { block: true, reason: "Dangerous command" };
    }
  }
});
```

> 典型用例（官方示例扩展）：`permission-gate.ts`（危险命令拦截，`ui.confirm`）、`protected-paths.ts`（禁止写入特定路径）、`inline-bash.ts`（工具调用内联 bash）。

### tool_result（中间件）
- 并行模式下，`tool_result` 与 `tool_execution_end` 按完成顺序交错；最终的 `toolResult` 消息事件稍后按助手源顺序发出。
- handler 链式执行，可修改结果。

---

## 九、交互式工具

扩展能力之一：可注册**交互式工具**——问题、向导、自定义对话框（`extensions.md` 开头能力列表）。用于需要向用户索取输入或展示自定义 UI 的场景（与默认自动工具调用相对）。

---

## 十、工具结果截断

为控制上下文体积，工具结果在序列化时**截断到 2000 字符**，超出部分替换为标记（标明被截断了多少字符）（`compaction.md`）。`read` 和 `bash` 的输出通常是上下文大小的最大贡献者，故大文件/长命令输出是重点。

---

## 十一、常见场景速查

| 目标 | 做法 |
|------|------|
| 只允许少数工具 | 启动 `pi --tools read,grep,find,ls ...` |
| 临时禁用某个工具 | `pi --exclude-tools ask_question` |
| 运行时切换只读 | `pi.setActiveTools(["read","bash"])` |
| 查看当前/全部工具 | `pi.getActiveTools()` / `pi.getAllTools()` |
| 注册新工具 | `pi.registerTool({...})`（无需 `/reload`） |
| 拦截危险命令 | `pi.on("tool_call", ...)` 返回 `{ block: true }` |
| 自定义工具改文件 | 用 `withFileMutationQueue()` 包裹读改写 |
| 让工具终态停止对话 | `execute` 返回 `terminate: true` |
| 工具报错 | 在 `execute` 中 `throw` |
| 引导模型用某工具 | `AGENTS.md` + `promptGuidelines`（写清工具名） |
