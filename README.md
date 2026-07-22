# my-knowledge-site

个人科研/技术知识库（MkDocs Material + GitHub Pages + Actions 自动部署）。

- 中文字体：**思源宋体（Source Han Serif SC）** + 代码 **JetBrains Mono**，均为自托管子集化 woff2（见 `docs/assets/fonts/`）。
- 公式：MathJax（由 `docs/javascripts/mathjax.js` + CDN 提供）。
- 中文搜索：jieba（构建时分词）。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdocs serve                     # http://127.0.0.1:8000
```

## 发布

```bash
git add .
git commit -m "docs: ..."
git push                         # Actions 自动构建并部署到 GitHub Pages
```

仓库 → Settings → Pages → Source 选 **GitHub Actions**。

## 发布已有笔记（含图片）

使用 `tools/publish.py` 将文章直接同步到二级目录，避免在左侧栏产生第三级文章目录：

```bash
python tools/publish.py --src "D:/Projects/Pi/Pi notes" --cat "ai/AI工具" "Pi Agent 工具操作速查笔记.md"
python tools/publish.py --src "D:/Projects/Pi/math" --cat "math/谱图理论" "谱图理论入门P1-综合笔记.md"
```

脚本输出 `docs/<一级目录>/<二级目录>/<文章>.md`。文章引用的本地图片会复制到该二级目录的 `images/`，并自动改名为“文章名前缀-原文件名”，同时改写 Markdown 图片链接，避免同名图片冲突。详见手册 §3.1。

## 重新生成字体子集（新增内容含生僻字时）

字体已按当前 `docs/` 内容 + 常用字子集化。若新增内容出现缺字（回退到系统衬线），
重新跑子集化即可：

```bash
pip install fonttools brotli
python tools/make_glyphs.py            # 由 docs/ 生成 glyphs.txt
pyftsubset OTF/SourceHanSerifSC-Regular.otf \
  --text-file=glyphs.txt \
  --output-file=docs/assets/fonts/SourceHanSerifSC-Regular.woff2 \
  --flavor=woff2 --no-hinting --layout-features='*'
```
