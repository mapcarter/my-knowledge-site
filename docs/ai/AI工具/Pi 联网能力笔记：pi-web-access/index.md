# Pi 联网能力笔记：pi-web-access

> 本文记录 `pi-web-access` 包的能力、配置与使用要点，弥补 Pi 默认"缺少联网搜索"的短板。
> 内容来源：pi.dev 包详情页（pi-web-access v0.13.0）+ 本机实际安装验证（2026-07-16）。
> 与本机其他笔记并列：`pi-sessions-cheatsheet.md`（会话）、`pi-tools-guide.md`（工具）。

---

## 一、包基本信息

| 项 | 值 |
|----|----|
| 名称 | `pi-web-access` |
| 版本 | 0.13.0（发布 Jun 25, 2026） |
| 作者 | nicopreme（GitHub: `nicobailon/pi-web-access`） |
| 许可 | MIT |
| 类型 | `extension` + `skill` |
| 大小 | 6.7 MB（5 依赖 + 4 peers） |
| 热度 | 139.2K/mo · 27.3K/wk 下载 |
| 最低 Pi 版本 | **v0.37.3+**（本机 0.80.7 ✓ 满足） |

**一句话定位**：为 Pi 提供 Web 搜索、URL 抓取、GitHub 仓库克隆、PDF 提取、YouTube 视频理解、本地视频分析。支持 OpenAI / Brave / Parallel / Tavily / Exa / Perplexity / Gemini。

---

## 二、本机安装与验证状态

安装命令（npm 全局包）：
```bash
pi install npm:pi-web-access
```
> 非交互/脚本环境下建议加 `--approve` 以避免信任提示卡住：`pi install npm:pi-web-access --approve`

**已验证（2026-07-16）**：
- `pi install` 成功：added 21 packages，0 vulnerabilities。
- `pi list` 已列出 `npm:pi-web-access`。
- **端到端验证通过**：让模型用 `web_search` 真实搜索，返回带引用源（`https://github.com/earendil-works/pi`）的结果 → 扩展加载、工具注册、模型调度、联网均正常。

**安装警告（已知、可忽略）**：
- `sharp@0.33.5` 的 install 脚本未被 `allow-scripts` 批准。仅影响**图片/视频帧**的预编译处理，**不影响文本搜索与网页抓取**。
- 若日后要用视频帧提取，运行 `npm approve-scripts sharp` 批准，或忽略（Gemini 转写/理解仍可用）。

---

## 三、零配置即可用

- **Exa MCP**：无需任何 API key 即可搜索（默认回退链兜底层）。
- **Codex auth 复用**：若你用 Codex 订阅登录了 Pi（`/login`），OpenAI 搜索可复用该 auth，无需单独 key。
- 想要更多引擎/直接 API 访问，再往 `~/.pi/web-search.json` 填 key（见第五节）。

---

## 四、核心工具（模型可自主调用）

### 1. `web_search`
搜索网络，返回**带引用来源的综合答案**。
```typescript
web_search({ query: "rust async programming" })
web_search({ queries: ["q1", "q2"] })                         // 批量
web_search({ query: "...", numResults: 10, recencyFilter: "week" })
web_search({ query: "...", domainFilter: ["github.com"] })   // 限域名；前缀 - 排除
web_search({ query: "...", provider: "openai" })             // 指定引擎
web_search({ query: "...", includeContent: true })           // 后台抓取全文
web_search({ queries: [...], workflow: "summary-review" })   // 策展工作流
```
参数：

| 参数 | 说明 |
|------|------|
| `query` / `queries` | 单条或批量查询 |
| `numResults` | 每条结果数（默认 5，最大 20） |
| `recencyFilter` | `day` / `week` / `month` / `year` |
| `domainFilter` | 限定域名（前缀 `-` 排除） |
| `provider` | `auto`（默认）/ `openai` / `brave` / `parallel` / `tavily` / `exa` / `perplexity` / `gemini` |
| `includeContent` | 后台抓取来源全文 |
| `workflow` | `none`（跳过策展）/ `summary-review`（开策展并自动起草摘要，默认）/ `auto-summary`（不开发布器直接生成摘要） |

### 2. `fetch_content`
抓取 URL 并提取为可读 markdown。**自动识别** GitHub 仓库 / YouTube 视频 / PDF / 本地视频 / 普通网页。
```typescript
fetch_content({ url: "https://example.com/article" })
fetch_content({ urls: ["u1","u2","u3"] })                     // 批量
fetch_content({ url: "https://github.com/owner/repo" })      // GitHub 克隆
fetch_content({ url: "https://youtube.com/watch?v=abc", prompt: "展示了哪些库？" })
fetch_content({ url: "/path/to/recording.mp4", prompt: "屏幕上出现什么错误？" })  // 本地视频
fetch_content({ url: "...", timestamp: "23:41-25:00", frames: 4 })  // 取帧
```
参数：

| 参数 | 说明 |
|------|------|
| `url` / `urls` | 单个 URL/路径或批量 |
| `prompt` | 对 YouTube / 本地视频提问 |
| `timestamp` | 取帧时间：单点 `"23:41"`、范围 `"23:41-25:00"`、秒 `"85"` |
| `frames` | 取帧数量（最大 12） |
| `forceClone` | 强制克隆超过 350MB 阈值的大仓库 |

### 3. `get_search_content`
检索**之前**搜索/抓取的存储内容（超 30000 字符会在工具响应中截断，但完整存储在此可回取）。
```typescript
get_search_content({ responseId: "abc123", urlIndex: 0 })
get_search_content({ responseId: "abc123", url: "https://..." })
get_search_content({ responseId: "abc123", query: "原始查询" })
```

---

## 五、能力详情与回退链

### 智能回退（Smart Fallbacks）
每个能力都有回退链，原则"总有一个能用"：

- **`web_search`（auto 模式）**：OpenAI（可用时）→ Exa（有 key 走直连，无 key 走 MCP）→ Brave → Parallel → Tavily → Perplexity → Gemini API → 启用浏览器 cookie 时 Gemini Web。
- **`fetch_content`**：
  - 视频文件？Gemini API → Gemini Web（cookie）
  - GitHub？克隆仓库，返回文件内容 + 本地路径
  - YouTube？Gemini Web（cookie）→ Gemini API → Perplexity
  - HTTP：PDF？提取文本存 `~/Downloads/`；HTML？Readability → RSC 解析 → Jina Reader → Gemini 兜底
  - 文本/JSON/Markdown？直接返回

### GitHub 仓库
- 克隆到本地而非抓取：根 URL 返回 repo tree + README；`/tree/` 返回目录列表；`/blob/` 返回文件内容。
- 超 350MB 走轻量 API 视图（`forceClone: true` 可强制全量）。
- Commit SHA URL 经 API 处理；克隆在会话内缓存，切换会话清除。
- 私有仓库需 `gh` CLI。

### YouTube 视频
- 经 Gemini 全视频理解：视觉描述、带时间戳转写、章节标记。传 `prompt` 可问具体问题，结果含缩略图供模型获得视觉上下文。
- 回退：Gemini Web（cookie）→ Gemini API → Perplexity（仅文本）。
- 支持所有格式：`/watch?v=`、`youtu.be/`、`/shorts/`、`/live/`、`/embed/`、`/v/`。

### 本地视频文件
- 传文件路径（`/`、`./`、`../`、`file://`）经 Gemini 分析；支持 MP4/MOV/WebM/AVI 等 ≤50MB；传 `prompt` 提问。
- 装 `ffmpeg` 时附带缩略帧。回退：Gemini API → Gemini Web（cookie）。

### 视频帧提取
- 对 YouTube 或本地视频用 `timestamp` + `frames` 取视觉帧为图片。
- 需 `ffmpeg`（YouTube 还需 `yt-dlp`）。时间格式支持 `H:MM:SS` / `MM:SS` / 裸秒。

### PDF
- 提取文本存为 markdown 到 `~/Downloads/`；模型可读特定段落，避免整文档进上下文。
- **仅文本提取，无 OCR。**

### 被拦截的页面
- Readability 失败或只剩 cookie 提示时，依次重试：Jina Reader（服务端渲染，无需 key）→ Gemini URL Context API → 启用 cookie 时 Gemini Web。透明处理 SPA、JS 重页、反爬；并解析 Next.js RSC flight data。

---

## 六、命令与交互

| 命令 | 说明 |
|------|------|
| `/websearch` | 直接打开搜索策展器；可预填 `/websearch react hooks, next.js caching`（逗号分隔）。结果在你批准摘要或"Send selected results without summary"时注入对话；超时自动提交并回退确定性摘要 |
| `/curator` | 运行时切换/配置策展工作流：`/curator on`(summary-review) / `off`(原始结果) / `summary-review`；持久化到 `~/.pi/web-search.json`，下次 `web_search` 生效 |
| `/search` | 交互浏览当前会话存储的搜索结果，列出 response IDs 便于回取 |
| `/google-account` | 显示 Gemini Web 当前认证的 Google 账号（多 Chromium profile 或设了 `chromeProfile` 时有用） |

**活动监视器**：`Ctrl+Shift+W` 实时查看请求/响应（API 调用、URL 抓取、状态码、耗时）。

---

## 七、Skills

- **`librarian`**：内置的开源库调研工作流，组合 GitHub 克隆 + web 搜索 + git 操作（blame/log/show），产出带 permalink 的证据支撑答案。Pi 按 prompt 自动加载，也可用 `/skill:librarian` 显式调用。

---

## 八、配置（`~/.pi/web-search.json`）

默认路径 `~/.pi/web-search.json`；若设了 `PI_CODING_AGENT_DIR` 或 `XDG_CONFIG_HOME/pi`，则为对应目录下的 `web-search.json`。**所有字段均可选**。

```json
{
  "openaiApiKey": "sk-...",
  "braveApiKey": "BSA-...",
  "exaApiKey": "exa-...",
  "parallelApiKey": "...",
  "tavilyApiKey": "tvly-...",
  "perplexityApiKey": "pplx-...",
  "geminiApiKey": "AIza...",
  "geminiBaseUrl": "https://my-gateway.example.com/gemini",
  "cloudflareApiKey": "...",
  "provider": "openai",
  "webSearch": { "enabled": true },
  "chromeProfile": "Profile 2",
  "allowBrowserCookies": false,
  "searchModel": "gemini-2.5-flash",
  "summaryModel": "anthropic/claude-haiku-4-5",
  "workflow": "summary-review",
  "curatorTimeoutSeconds": 20,
  "githubClone": {
    "enabled": true,
    "maxRepoSizeMB": 350,
    "cloneTimeoutSeconds": 30,
    "clonePath": "/tmp/pi-github-repos"
  },
  "youtube": { "enabled": true, "preferredModel": "gemini-3-flash-preview" }
}
```

常用开关：
- `provider`：默认搜索引擎（`auto` 走回退链）。
- `allowBrowserCookies`：开启后可用 Gemini Web（需本地 Chromium 登录态）。
- `workflow` / `/curator`：控制是否经策展器。
- `githubClone.*`：克隆行为（阈值、超时、路径）。

---

## 九、安全与注意事项

- **第三方代码**：官方明确警告 *"Pi packages can execute code and influence agent behavior. Review the source before installing third-party packages."* 安装即运行其代码，装前建议过一眼 GitHub 源码（`nicobailon/pi-web-access`）。
- **出网流量**：该包会向各搜索引擎/抓取服务发请求，注意网络与隐私。
- **进上下文**：搜索结果、抓取内容会进入对话上下文（你之前了解过工具结果截断机制；本包另有 `get_search_content` 按需回取、30k 截断存储来控体积）。
- **工具池**：注册 `web_search`/`fetch_content`/`get_search_content` 等。若担心工具集膨胀影响 token，可用 `--exclude-tools` 或扩展内 `setActiveTools` 收窄，或用 `/curator off` 关策展。

---

## 十、常用操作速查

```bash
# 安装 / 卸载
pi install npm:pi-web-access [--approve]
pi remove npm:pi-web-access

# 查看是否已安装
pi list

# 对话中（模型自主调用）
"搜索一下 Pi coding agent 的最新版本"
"抓取这个页面并提取要点：https://..."
"把这个 GitHub 仓库克隆下来帮我看看结构：https://github.com/owner/repo"
"看下这个 YouTube 视频讲了什么：https://youtube.com/watch?v=abc"

# 交互命令
/websearch            # 打开策展器先审结果
/curator off          # 关闭策展，拿原始结果
/search               # 浏览已存搜索结果
Ctrl+Shift+W          # 活动监视器
```

> 卸载：`pi remove npm:pi-web-access`。配置 `~/.pi/web-search.json` 与 `~/.pi` 下的克隆缓存需手动清理。
