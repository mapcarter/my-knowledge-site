#!/usr/bin/env python3
"""把笔记连同图片同步进 docs/，采用"每篇笔记一个文件夹"结构，彻底避免同名图片冲突。

结构（关键）：
  docs/<cat>/<笔记名>/index.md
  docs/<cat>/<笔记名>/images/...

每篇笔记的图片都待在自己文件夹里。即使两篇笔记都有 images/figure1.png，
也分别在 docs/math/甲/images/ 与 docs/physics/乙/images/，互不覆盖；
相对链接 images/xxx.png 依旧有效，无需任何路径改写。

用法：
  python tools/publish.py --src "D:/Projects/Pi/math" --cat math "谱图理论入门P1-综合笔记.md"
  python tools/publish.py --src "D:/Projects/Pi/physics" --cat physics "另一篇.md"

说明：
  - 重新发布同一篇（内容更新）会刷新该文件夹。
  - 若两篇不同笔记恰巧同名且发到同一分类，后发的会覆盖先发的——请保证笔记名唯一。
"""
import argparse
import pathlib
import re
import shutil
import sys

IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="笔记所在源目录")
    ap.add_argument("--dest", default="docs", help="项目 docs 目录")
    ap.add_argument("--cat", default="", help="目标分类子目录（留空放 docs 根）")
    ap.add_argument("files", nargs="+", help="要发布的 .md 文件名（相对于 --src）")
    args = ap.parse_args()

    src = pathlib.Path(args.src).resolve()
    dest_root = (pathlib.Path(args.dest) / args.cat).resolve()

    for name in args.files:
        md = src / name
        if not md.exists():
            print(f"[跳过] 找不到 {md}", file=sys.stderr)
            continue

        stem = md.stem
        note_dir = dest_root / stem

        # 刷新：同一篇笔记重新发布时清掉旧副本再写
        if note_dir.exists():
            shutil.rmtree(note_dir)
        note_dir.mkdir(parents=True, exist_ok=True)

        # 1) 笔记存为 index.md
        shutil.copy2(md, note_dir / "index.md")

        # 2) 同级 images/ 整体复制（与笔记同文件夹，天然隔离，不与他人冲突）
        imgs_dir = src / "images"
        if imgs_dir.is_dir():
            shutil.copytree(imgs_dir, note_dir / "images", dirs_exist_ok=True)

        # 3) 同级被直接引用的孤立本地图（如根目录 01.png）
        text = (note_dir / "index.md").read_text(encoding="utf-8")
        for ref in IMG_RE.findall(text):
            ref = ref.strip()
            if ref.startswith(("http://", "https://", "//")):
                continue
            if ref.startswith("images/") or ref.startswith("./images/"):
                continue
            ref_path = (src / ref).resolve()
            if ref_path.exists() and ref_path.suffix.lower() in IMG_EXTS:
                shutil.copy2(ref_path, note_dir / ref_path.name)

        print(f"[完成] {name} -> docs/{args.cat}/{stem}/ (index.md + images/)")


if __name__ == "__main__":
    main()
