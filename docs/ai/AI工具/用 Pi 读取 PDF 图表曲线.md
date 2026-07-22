# 用 Pi 读取 PDF 图表 / 曲线（HY3 + 视觉模型）

> 适用场景：主模型是 `tencent/hy3:free`（OpenRouter，非多模态），但需要理解 PDF 里的
> 插图、曲线、架构图、热力图等图像内容。
> 核心思路：**HY3 当大脑，免费视觉模型当眼睛，`describe_image` 当桥**——单 agent
> 通过工具调用把图委托给视觉模型，结果以文字返回给 HY3 继续推理。不推荐为多 agent
> 小队（pi-team / pi-parallel-agents）方案，对读单篇论文属于过度工程。

---

## 1. 问题本质
- HY3 是非多模态模型，无法接收/理解图片像素。PDF 里的**文字、文本型表格**可用
  `pdftotext` 提取（含图注 caption），但**图像内容读不了**。
- 这不是工作目录 / 路径问题，是模型能力问题。解决靠"文本模型 + 视觉模型"分工。

## 2. 所需组件
| 组件 | 作用 | 来源 |
|---|---|---|
| `pi-vision-tool` | 提供 `describe_image` 工具 + `/vision` 命令 | npm 包（Pi 包注册中心 pi.dev） |
| `pdftoppm` | PDF 页 → PNG（替代装不了的 `pi-pdf`） | poppler 套件，与 `pdftotext` 同源 |
| 视觉模型 | 实际"看"图的模型 | OpenRouter 上的免费视觉模型 |

> 注：`pi-pdf`（github.com/joemccanna/pi-pdf）当前 **404 无法安装**，其"PDF 转图"
> 功能由环境已有的 `pdftoppm` 完全替代，方案不缺环节。

## 3. 安装
```bash
# 若 npm 报 EPERM（node_cache 在 Program Files 下无写权），先把 cache 移到用户目录：
npm config set cache "$USERPROFILE/.npm-cache"

# 安装视觉工具包（--approve 非交互确认）
pi install npm:pi-vision-tool --approve
```
安装后 `pi-vision-tool` 会被写入 `~/.pi/agent/settings.json` 的 `packages`。

## 4. 配置（两个文件，均在 `~/.pi/agent/`）
### 4.1 `models.json` —— 定义视觉模型 provider + 模型列表
Pi 启动时会读取此文件并注册到 model registry。内容示例（**apiKey 填与 HY3 同一个
OpenRouter key**，即 `~/.pi/agent/auth.json` 里 `openrouter.key` 的值；HY3 和视觉模型
共用一把 key 即可）：

```json
{
  "providers": {
    "openrouter-vision": {
      "baseUrl": "https://openrouter.ai/api/v1",
      "apiKey": "sk-or-...（与 auth.json 的 openrouter.key 相同）",
      "api": "openai-completions",
      "models": [
        {
          "id": "google/gemma-4-31b-it:free",
          "name": "Gemma 4 31B IT (vision, free) - default",
          "input": ["text", "image"],
          "contextWindow": 262144,
          "maxTokens": 8192
        },
        {
          "id": "google/gemma-4-26b-a4b-it:free",
          "name": "Gemma 4 26B A4B IT (vision, free)",
          "input": ["text", "image"],
          "contextWindow": 262144,
          "maxTokens": 8192
        },
        {
          "id": "nvidia/nemotron-nano-12b-v2-vl:free",
          "name": "Nemotron Nano 12B V2 VL (vision, free)",
          "input": ["text", "image"],
          "contextWindow": 128000,
          "maxTokens": 4096
        }
      ]
    }
  }
}
```
> 选模型前务必核实其 `input_modalities` 含 `"image"`（OpenRouter 公开列表
> `https://openrouter.ai/api/v1/models` 可查；单模型端点匿名会 404，属正常）。
> Gemma 4 系列、Nemotron-*VL 支持图像；纯文本模型（如旧 Gemma / Llama 非视觉版）不行。

### 4.2 `vision-tool.json` —— 绑定当前使用的 provider / model
```json
{
  "provider": "openrouter-vision",
  "model": "google/gemma-4-31b-it:free",
  "enabled": true
}
```
> `provider` / `model` 必须与 `models.json` 里的名字**完全一致**。

## 5. 使用流程（pipeline）
1. **PDF → 图**（HY3 用 bash 调 `pdftoppm`）：
   ```bash
   pdftoppm -png -r 150 -f <起始页> -l <结束页> "论文.pdf" ./out_prefix
   # 例：转第 3 页
   pdftoppm -png -r 150 -f 3 -l 3 "xxx.pdf" ./fig3
   # 生成 ./fig3-03.png
   ```
2. **看图**：直接对 HY3 下指令，例如
   > "用 describe_image 读 ./fig3-03.png 里的 Figure 3 学习曲线，
   > 描述各模型验证误差随 epoch 的变化趋势"
   HY3 会调用 `describe_image`：
   - `image_path`：PNG 路径（也支持 data URL / raw base64；不接受 http(s) URL）
   - `prompt`：具体要看什么（描述 / 提取文字 / 坐标 / 分析）
   - `compress`：`true` 一般（更快、省 token）；像素级精确（坐标、细字、颜色）设 `false`
   - `reasoning`：`off`（快）/ `medium`~`xhigh`（复杂图，如架构图、需多步推理）
3. **整合**：视觉模型返回文字描述 → HY3 结合图注（caption）给出完整解读。

## 6. 切换视觉模型
在 Pi 会话内用 `/vision` 命令（即时生效，无需 `/reload`，配置存到 `vision-tool.json`）：
```bash
/vision config model nvidia/nemotron-nano-12b-v2-vl:free   # 切换模型
/vision config provider openrouter-vision                  # 切换 provider（一般不用）
/vision                                                    # 无参：查看当前配置
/vision on | /vision off                                   # 启用 / 禁用工具
```
当前预置的三个免费视觉模型（任选）：
- `google/gemma-4-31b-it:free`（默认）
- `google/gemma-4-26b-a4b-it:free`
- `nvidia/nemotron-nano-12b-v2-vl:free`

新增 / 更换模型：编辑 `models.json` 的 `models` 数组（加一项带 `"input":["text","image"]`
的模型），再 `/vision config model <新id>`。

## 7. 启用
改完 `models.json` / `vision-tool.json` / 刚装包后，**退出当前 Pi 会话、新开一个会话**
即可加载。

## 8. 注意事项 / 排错
- **免费额度 per-key 共享**：HY3（hy3:free）与视觉模型走同一把 OpenRouter key，
  两者免费速率 / 额度会互相挤占，频繁看图更易触发限流。遇限流可换付费模型或单独 key。
- **曲线精确数值 ≠ 看图得到**：视觉模型给趋势和"大致"数值；要精确坐标点，仍需
  从论文 Table（文本可精确读）或代码 / 数据还原。
- **图像优化**：`pi-vision-tool` 会自动把图缩到 1568px、转 JPEG（85）再发，可用
  环境变量 `PI_VISION_MAX_DIM` / `PI_VISION_JPEG_QUALITY` / `PI_VISION_COMPRESS=false`
  调整；依赖 `sharp`（装包时若有 install script 未批准，会回退发原图，仍可用）。
- **JSON 合法性**：改 `models.json` 后建议校验
  `python -c "import json,os;json.load(open(os.path.expanduser('~/.pi/agent/models.json')))"`。
- **`provider`/`model` 名必须两边一致**，否则 `describe_image` 报 "not configured"。

## 9. 实例：DCRNN 论文（Diffusion Convolutional Recurrent Neural Network）
目标文件：`D:/Dropbox/Work/交通预测/DCRNN/Diffusion Convolutional Recurrent Neural Network Data-Driven Traffic Forecasting.pdf`（16 页）
- 文字 / 图注 / Table 1：已用 `pdftotext -layout` 提取为 `dcrnn_text.txt`。
- 需"看"的图：Figure 1（空间相关性）、Figure 3（学习曲线）、Figure 4（K 敏感度）、
  Figure 5（变体对比）、Figure 6（预测可视化）、Figure 7（局部滤波器）。
- 读法：先用 `pdftoppm` 把对应页转 PNG，再 `describe_image` 让视觉模型描述曲线趋势 /
  峰值 / 各模型差异，HY3 结合 caption 综合。
- 注意：`pdftoppm` 转图可能出现 `No display font for 'ArialUnicode'` 字体警告，仅影响
  文字字形渲染，不影响曲线图形，可忽略。
