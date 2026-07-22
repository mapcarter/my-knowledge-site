#!/usr/bin/env python3
"""把笔记同步进 docs/，文章直接放在目标二级目录下。

结构（关键）：
  docs/<cat>/<文章名>.md
  docs/<cat>/images/<文章名>-<原图片名>...

文章不再使用“文章名/index.md”文件夹，因此不会在 MkDocs 左侧栏中产生额外的第三级目录。
图片集中在目标二级目录的 images/ 下，并使用文章名前缀避免不同文章之间的同名图片冲突；
脚本会同步改写 Markdown 中对应的本地图片链接。

用法：
  python tools/publish.py --src "D:/Projects/Pi/Pi notes" --cat "ai/AI工具" "笔记.md"

说明：
  - 重新发布同一篇会刷新目标 .md，并覆盖该文章前缀对应的图片。
  - 图片目录只复制源目录中被文章引用的本地图；远程图片不会复制。
  - 若文章引用的图片位于源目录的 images/ 下，发布后链接仍为 images/文件名，只是文件名会加文章前缀。
"""
import argparse
import pathlib
import re
import shutil
import sys

IMG_RE = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")
IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
REMOTE_PREFIXES = ("http://", "https://", "//", "data:")


def safe_name(path: pathlib.Path) -> str:
    """用于图片前缀，保留中文但移除路径分隔符等不安全字符。"""
    return re.sub(r'[<>:"/\\|?*]', "_", path.stem).strip() or "note"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="笔记所在源目录")
    ap.add_argument("--dest", default="docs", help="项目 docs 目录")
    ap.add_argument("--cat", default="", help="目标二级目录（相对于 docs）")
    ap.add_argument("files", nargs="+", help="要发布的 .md 文件名（相对于 --src）")
    args = ap.parse_args()

    src = pathlib.Path(args.src).resolve()
    dest_root = (pathlib.Path(args.dest) / args.cat).resolve()
    images_root = dest_root / "images"

    for name in args.files:
        md = src / name
        if not md.is_file():
            print(f"[跳过] 找不到 {md}", file=sys.stderr)
            continue

        stem = md.stem
        target = dest_root / md.name
        dest_root.mkdir(parents=True, exist_ok=True)
        images_root.mkdir(parents=True, exist_ok=True)

        # 刷新同一篇文章及其此前生成的图片，避免旧内容残留。
        target.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
        prefix = safe_name(md)
        for old_image in images_root.glob(f"{prefix}-*"):
            if old_image.is_file():
                old_image.unlink()

        text = target.read_text(encoding="utf-8")
        rewritten = []
        for match in IMG_RE.finditer(text):
            ref = match.group(2).strip()
            if ref.startswith(REMOTE_PREFIXES):
                continue

            # Markdown 图片链接可能带标题，例如 images/a.png "caption"。
            ref_path_text, separator, title = ref.partition(" ")
            source_image = (src / ref_path_text).resolve()
            if not source_image.is_file() or source_image.suffix.lower() not in IMG_EXTS:
                continue

            target_name = f"{prefix}-{source_image.name}"
            shutil.copy2(source_image, images_root / target_name)
            new_ref = f"images/{target_name}"
            if separator:
                new_ref += f" {title}"
            rewritten.append((match.group(0), f"{match.group(1)}{new_ref}{match.group(3)}"))

        for old, new in rewritten:
            text = text.replace(old, new)
        target.write_text(text, encoding="utf-8")
        print(f"[完成] {name} -> docs/{args.cat}/{md.name}")


if __name__ == "__main__":
    main()
