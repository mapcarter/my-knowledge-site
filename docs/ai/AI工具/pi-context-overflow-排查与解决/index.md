# Pi Agent 上下文长度超限（400）排查与解决手册

> 适用场景：Pi Agent 调用模型时报 `Error: 400 ... maximum context length ...`，
> 错误信息中包含 `(X of text input, Y of tool input, Z in the output)` 的 token 拆分。
>
> 本文基于一次真实故障排查整理，结论均经过源码与配置文件验证。

---

## 1. 问题现象

Pi Agent 读取多个 Markdown 文档时，模型 API 直接返回 400 错误，原文如下：

```
Error: 400: {"message":"This endpoint's maximum context length is 262144 tokens.
However, you requested about 265420 tokens
(21809 of text input, 2643 of tool input, 240968 in the output).
Please reduce the length of either one, or use the context-compression plugin
to compress your prompt automatically.","code":400,"metadata":{"provider_name":null}}
```

### 1.1 错误数字拆解

| 组成部分 | 数量 | 含义 |
|---|---|---|
| text input | 21809 | 系统提示 + 对话历史 |
| tool input | 2643 | 工具定义（schema） |
| **output** | **240968** | **Pi 为模型"回复"预留的 `max_tokens` 输出预算** |
| **端点硬上限** | **262144** | 该模型/端点允许的最大上下文 |
| **实际请求** | **265420** | 超出上限约 **3276** tokens |

### 1.2 最直接的误解（务必先排除）

> ❌ 误以为"我读的三个文档太大了，要少读 / 分块读"。

**真相**：你真正发给模型的 prompt 只有 `21809 + 2643 ≈ 24.5K` tokens，并不大。
真正的巨无霸是 **`output` = 240968** —— Pi 试图把几乎整个 256K 窗口都留给模型输出。
所以问题不在"输入太大"，而在"输出预算被撑满"。

---

## 2. 根本原因

### 2.1 Pi 如何计算 `max_tokens`

Pi 在每次发请求前，会把"输出预算"尽量撑满整个上下文窗口。逻辑位于：

```
D:\Program Files\nodejs\node_global\node_modules\@earendil-works\pi-coding-agent\node_modules\@earendil-works\pi-ai\dist\api\simple-options.js
```

```js
const CONTEXT_SAFETY_TOKENS = 4096;
export function clampMaxTokensToContext(model, context, maxTokens) {
    if (model.contextWindow <= 0) return Math.max(MIN_MAX_TOKENS, maxTokens);
    const available = model.contextWindow
                      - estimateContextTokens(context).tokens
                      - CONTEXT_SAFETY_TOKENS;          // 减 4096 安全余量
    return Math.min(maxTokens, Math.max(MIN_MAX_TOKENS, available));
}
```

即：`输出预算 = min(模型 maxTokens, contextWindow − 估算输入 − 4096)`。

当模型的 `maxTokens` 被配置成和 `contextWindow` 一样大（例如都是 262144）时，
`min(262144, 262144 − 输入 − 4096)` 就会返回一个极接近窗口上限的值 —— 这正是报错的 240968。

### 2.2 本次故障的具体模型

排查 `settings.json` 发现默认模型并非 `models.json` 里那三个带视觉的模型，而是：

```json
// C:\Users\LX\.pi\agent\settings.json
{
  "defaultProvider": "openrouter",
  "defaultModel": "tencent/hy3:free",
  "defaultThinkingLevel": "medium"
}
```

`tencent/hy3:free` 是**内置 `openrouter` provider** 的模型，在 Pi 内置模型目录中配置为：

```json
// C:\Users\LX\.pi\agent\models-store.json
{
  "id": "tencent/hy3:free",
  "reasoning": true,
  "contextWindow": 262144,
  "maxTokens": 262144        // ← 元凶：输出预算上限 = 整个窗口
}
```

代入 2.1 的公式：
`min(262144, 262144 − 约18000 − 4096) ≈ 240048` → 与报错里的 **240968** 完全吻合。

### 2.3 为什么你 `models.json` 里那三个模型没问题

`models.json` 里定义的是 `openrouter-vision` provider 下的三个模型（Gemma / Nemotron），
它们已经显式设了 `maxTokens: 8192 / 4096`，所以输出被牢牢压住，不会触顶。
**报错用的是默认模型 `tencent/hy3:free`，它根本不在 `models.json` 中，而是走内置 provider。**

### 2.4 为什么没有自动压缩恢复

Pi 的自动溢出恢复（`agent-session.js` 的 `isContextOverflow` / compact+retry）主要匹配
OpenRouter 等特定的报错文案正则。本次报错的 `"maximum context length ... in the output"`
格式不匹配预设正则，因此**没有触发自动压缩**，原始 400 被直接抛出。

---

## 3. 解决方案

### ✅ 方案二（已实施，推荐）：用 `modelOverrides` 压低 `maxTokens`

关键点：**报错模型是内置模型**，所以要用 `modelOverrides`（而非在 `models:` 里新增模型）
来覆盖它的参数，且**不会替换**该 provider 的其他内置模型
（依据 `docs/models.md` 第 320/341/362 行说明）。

修改文件：`C:\Users\LX\.pi\agent\models.json`

```jsonc
{
  "providers": {
    // ↓↓↓ 新增：针对内置 openrouter 的模型覆盖 ↓↓↓
    "openrouter": {
      "modelOverrides": {
        "tencent/hy3:free": {
          "maxTokens": 32000,     // 核心：单次回复上限锁在 32K
          "contextWindow": 250000 // 双保险：按 250K 计算窗口，留出余量
        }
      }
    },
    // ↓↓↓ 原有配置保持不变 ↓↓↓
    "openrouter-vision": {
      "baseUrl": "https://openrouter.ai/api/v1",
      "apiKey": "sk-or-v1-xxxxxxxx",   // 注意：实际文件含真实 key，本文已脱敏
      "api": "openai-completions",
      "models": [ /* ... 三个视觉模型 ... */ ]
    }
  }
}
```

**生效验证**：无需重启 Pi，`models.json` 在每次打开 `/model` 时重新加载。
直接重跑原任务即可；可用 `pi --list-models` 查看该模型的 `maxOut` 是否变为 32K。

**效果**：请求总量从 265420 降到 `24.5K 输入 + 32K 输出 ≈ 56.5K`，远在 262144 以内。

### 其他可选方案（按场景选择）

| 方案 | 做法 | 适用场景 |
|---|---|---|
| **方案一：调小 `contextWindow`** | 在 `modelOverrides` 把 `contextWindow` 设成略小于端点真实上限（如 250000） | 不想限制回复长度，只留安全余量 |
| **`/compact` 手动压缩** | 会话中执行 `/compact`，或调 `~/.pi/agent/settings.json` 的 `compaction` 参数 | 会话历史本身已经很长 |
| **换更大上下文模型** | 换 1M 上下文模型，在 `modelOverrides` 把 `contextWindow` 调到实际值 | 确有超长上下文需求 |
| **分块读超大文档** | 用 `read` 的 `offset`/`limit` 分块读取 | 文档本身真的有几十万 token（本次不是） |

> 注意：本例中"少读文档"无效——输入仅 24.5K，瓶颈在输出预算。

---

## 4. 未来遇到类似问题的快速诊断流程

```
看到 400 "maximum context length" 错误
        │
        ├─ 看报错里的 "(X of text input, Y of tool input, Z in the output)"
        │
        ├─ 若 "in the output" 数字 ≈ contextWindow − 输入 − 4096
        │     → 该模型 maxTokens 被设得 ≈ contextWindow（典型：免费/推理模型）
        │     → 解法：给该模型加 modelOverrides 压低 maxTokens（见第 3 节）
        │
        ├─ 确认"当前实际用的模型"是谁
        │     → 查 C:\Users\LX\.pi\agent\settings.json 的 defaultModel/defaultProvider
        │     → 或 Pi 底部状态栏 / 会话 footer 显示的模型 id
        │
        ├─ 该模型是"内置模型"还是"自定义模型"？
        │     ├─ 内置（如 openrouter 下的 tencent/hy3:free）
        │     │     → 在 models.json 给对应 provider 加 modelOverrides
        │     └─ 自定义（在 models.json 的 models: 里）
        │           → 直接在该模型定义里加 "maxTokens": 32000
        │
        └─ 改完 models.json，重跑任务 / 打开 /model 重新加载即可
```

### 4.1 一句话判定法

> 只要报错里 **`in the output` 的数值接近端点上限**，就说明是"输出预算被撑满"，
> 统一解法：**给该模型设 `maxTokens` 上限（建议 32000）**。

---

## 5. 关键文件与位置速查

| 内容 | 路径 |
|---|---|
| 用户模型/provider 配置 | `C:\Users\LX\.pi\agent\models.json` |
| 默认模型/provider 选择 | `C:\Users\LX\.pi\agent\settings.json`（`defaultModel` / `defaultProvider`） |
| Pi 内置模型目录（含各模型 `contextWindow`/`maxTokens`） | `C:\Users\LX\.pi\agent\models-store.json` |
| `max_tokens` 计算逻辑 | `...\pi-coding-agent\node_modules\@earendil-works\pi-ai\dist\api\simple-options.js`（`clampMaxTokensToContext`） |
| 自动溢出检测/恢复逻辑 | `...\pi-coding-agent\dist\core\agent-session.js`（`isContextOverflow` / `_runAutoCompaction`） |
| 压缩（compaction）机制文档 | `...\pi-coding-agent\docs\compaction.md` |
| 模型/provider 配置文档 | `...\pi-coding-agent\docs\models.md`（`modelOverrides` 章节） |

---

## 6. 结论（速记）

- **现象**：400 错误，拆分里 `output` ≈ 窗口上限，总请求略超端点上限。
- **根因**：默认模型 `tencent/hy3:free` 的 `maxTokens=262144`，Pi 把整个窗口留给输出，
  加安全余量后略微超过端点真实 262144 上限。
- **解法**：在 `models.json` 用 `modelOverrides` 把该模型 `maxTokens` 降到 32000
  （并可选把 `contextWindow` 保守设为 250000）。
- **经验**：`in the output` 接近上限 = 输出预算被撑满 = 设 `maxTokens` 上限即可，
  与"输入/文档大小"基本无关。
