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

笔记若自带 `images/` 子文件夹，用 `tools/publish.py` 一键同步进 `docs/`。脚本会为**每篇笔记建一个文件夹**（`docs/<分类>/<笔记名>/index.md` + 同文件夹 `images/`），天然避免同名图片冲突，且不改任何路径：

```bash
python tools/publish.py --src "D:/Projects/Pi/math" --cat math "谱图理论入门P1-综合笔记.md"
python tools/publish.py --src "D:/Projects/Pi/physics" --cat physics "另一篇.md"
```

详见手册 §3.1（图片不用集中、不用改路径；同名图片靠"每篇一个文件夹"隔离）。

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
