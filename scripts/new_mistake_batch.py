#!/usr/bin/env python3
"""JLPT 错题批次半自动入库工具。"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
from pathlib import Path


SCREENSHOT_RE = re.compile(r"Screenshot[_ -](\d{8})[_ -]\d{6}", re.IGNORECASE)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

TYPE_LABELS = {
    "bunpou": "文法",
    "goi": "語彙",
    "kanji": "漢字",
    "bunpou-goi": "文法・語彙",
    "bunpou-kumitate": "文の組み立て",
    "reading": "読解",
    "listening": "聴解",
}

TYPE_INDEX_DIRS = {
    "bunpou": ["bunpou"],
    "goi": ["vocabulary"],
    "kanji": ["kanji"],
    "bunpou-goi": ["bunpou", "vocabulary"],
    "bunpou-kumitate": ["bunpou", "bunpou-kumitate"],
    "reading": ["reading"],
    "listening": ["listening"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="归档 Screenshot 图片，并生成 JLPT 错题批次模板。"
    )
    parser.add_argument("--date", help="批次日期，格式 YYYY-MM-DD。默认从截图文件名推断。")
    parser.add_argument("--type", required=True, help="题型，例如 kanji、bunpou-goi、bunpou-kumitate、reading。")
    parser.add_argument("--count", type=int, help="题数。默认使用本次归档截图数量。")
    parser.add_argument("--level", default="n2", help="级别，默认 n2。")
    parser.add_argument("--title", help="笔记标题。默认自动生成。")
    parser.add_argument(
        "--source-dir",
        default=".",
        help="截图来源目录。默认项目根目录。",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="项目根目录。默认当前目录。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览动作，不移动图片，不创建文件。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="允许覆盖已存在的批次模板文件。",
    )
    return parser.parse_args()


def validate_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"日期格式不正确: {value}，请使用 YYYY-MM-DD。") from exc


def date_from_filename(path: Path) -> dt.date | None:
    match = SCREENSHOT_RE.search(path.name)
    if not match:
        return None
    raw = match.group(1)
    return dt.date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))


def find_screenshots(source_dir: Path, batch_date: dt.date | None) -> list[Path]:
    files: list[Path] = []
    for path in sorted(source_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        if not path.name.lower().startswith("screenshot"):
            continue
        inferred = date_from_filename(path)
        if batch_date and inferred and inferred != batch_date:
            continue
        files.append(path)
    return files


def infer_batch_date(args_date: str | None, screenshots: list[Path]) -> dt.date:
    if args_date:
        return validate_date(args_date)
    dates = {date_from_filename(path) for path in screenshots}
    dates.discard(None)
    if len(dates) == 1:
        return dates.pop()  # type: ignore[return-value]
    if not dates:
        raise SystemExit("没有提供 --date，也无法从截图文件名推断日期。")
    formatted = ", ".join(sorted(date.isoformat() for date in dates))
    raise SystemExit(f"找到多个截图日期: {formatted}。请使用 --date 指定本次批次。")


def unique_destination(dest_dir: Path, name: str) -> Path:
    candidate = dest_dir / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        next_candidate = dest_dir / f"{stem}-{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def move_screenshots(
    screenshots: list[Path], dest_dir: Path, dry_run: bool
) -> list[Path]:
    moved: list[Path] = []
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    for src in screenshots:
        dest = unique_destination(dest_dir, src.name)
        moved.append(dest)
        if not dry_run:
            shutil.move(str(src), str(dest))
    return moved


def markdown_link(from_file: Path, target: Path) -> str:
    return os.path.relpath(target, start=from_file.parent).replace(os.sep, "/")


def make_batch_path(repo_root: Path, batch_date: dt.date, level: str, kind: str, count: int) -> Path:
    year = f"{batch_date:%Y}"
    month = f"{batch_date:%m}"
    filename = f"{batch_date.isoformat()}-{level.lower()}-{kind}-{count:02d}-items.md"
    return repo_root / "mistakes" / year / month / filename


def load_template(repo_root: Path) -> str:
    template_path = repo_root / "templates" / "mistake_batch.md"
    if not template_path.exists():
        raise SystemExit(f"找不到模板文件: {template_path}")
    return template_path.read_text(encoding="utf-8")


def vault_path(repo_root: Path, target: Path) -> str:
    """返回供 Obsidian 双链与嵌入使用的仓库根相对路径。"""
    return target.relative_to(repo_root).as_posix()


def wikilink(repo_root: Path, target: Path, label: str) -> str:
    link = vault_path(repo_root, target)
    if link.endswith(".md"):
        link = link[:-3]
    return f"[[{link}|{label}]]"


def image_markdown(repo_root: Path, images: list[Path]) -> str:
    if not images:
        return "- 本次没有自动归档新截图。"
    lines = []
    for image in images:
        link = vault_path(repo_root, image)
        lines.append(f"- ![[{link}]]")
    return "\n".join(lines)


def overview_rows(count: int) -> str:
    return "\n".join(
        f"| {index} |  |  |  |  |  |" for index in range(1, count + 1)
    )


def item_sections(count: int, kind: str) -> str:
    sections: list[str] = []
    is_ordering = kind == "bunpou-kumitate"
    is_kanji = kind == "kanji"
    for index in range(1, count + 1):
        if is_ordering:
            sections.append(
                "\n".join(
                    [
                        f"### {index}. 文の組み立て",
                        "",
                        "#### 原题完整记录（不要加工）",
                        "",
                        "- 题干:",
                        "- 空格形式:",
                        "",
                        "#### 原题排序形式",
                        "",
                        "> ＿＿ ＿＿ ★ ＿＿",
                        "",
                        "#### 选项",
                        "",
                        "1. ",
                        "2. ",
                        "3. ",
                        "4. ",
                        "",
                        "#### 你的答案 / 正解",
                        "",
                        "- 你的答案:",
                        "- 正解:",
                        "",
                        "#### 正确顺序",
                        "",
                        "- 顺序:",
                        "- ★答案:",
                        "",
                        "#### 还原过程",
                        "",
                        "- ",
                        "",
                        "#### 完整句",
                        "",
                        "> ",
                        "",
                        "#### 中文翻译",
                        "",
                        "- ",
                        "",
                        "#### 整句翻译",
                        "",
                        "> ",
                        "",
                        "#### 整句拆解",
                        "",
                        "| 片段 | 意思 | 说明 |",
                        "|---|---|---|",
                        "|  |  |  |",
                        "",
                        "#### 高频考点",
                        "",
                        "- ",
                        "",
                        "#### 下次怎么判断",
                        "",
                        "- ",
                    ]
                )
            )
        elif is_kanji:
            sections.append(
                "\n".join(
                    [
                        f"### {index}. 漢字",
                        "",
                        "#### 原题完整记录（不要加工）",
                        "",
                        "- 题干:",
                        "- 划线词:",
                        "",
                        "#### 选项",
                        "",
                        "1. ",
                        "2. ",
                        "3. ",
                        "4. ",
                        "",
                        "#### 你的答案 / 正解",
                        "",
                        "- 你的答案:",
                        "- 正解:",
                        "",
                        "#### 中文翻译",
                        "",
                        "- ",
                        "",
                        "#### 整句翻译",
                        "",
                        "> ",
                        "",
                        "#### 整句拆解",
                        "",
                        "| 片段 | 意思 | 说明 |",
                        "|---|---|---|",
                        "|  |  |  |",
                        "",
                        "#### 为什么这样选",
                        "",
                        "- ",
                        "",
                        "#### 错因",
                        "",
                        "- ",
                        "",
                        "#### 高频考点",
                        "",
                        "- 读音:",
                        "- 字形:",
                        "- 常见搭配:",
                        "",
                        "#### 例句",
                        "",
                        "- ",
                    ]
                )
            )
        else:
            sections.append(
                "\n".join(
                    [
                        f"### {index}. ",
                        "",
                        "#### 原题完整记录（不要加工）",
                        "",
                        "- 题干:",
                        "",
                        "#### 选项",
                        "",
                        "1. ",
                        "2. ",
                        "3. ",
                        "4. ",
                        "",
                        "#### 你的答案 / 正解",
                        "",
                        "- 你的答案:",
                        "- 正解:",
                        "",
                        "#### 中文翻译",
                        "",
                        "- ",
                        "",
                        "#### 整句翻译",
                        "",
                        "> ",
                        "",
                        "#### 整句拆解",
                        "",
                        "| 片段 | 意思 | 说明 |",
                        "|---|---|---|",
                        "|  |  |  |",
                        "",
                        "#### 为什么这样选",
                        "",
                        "- ",
                        "",
                        "#### 错因",
                        "",
                        "- ",
                        "",
                        "#### 高频考点",
                        "",
                        "- ",
                        "",
                        "#### 例句",
                        "",
                        "- ",
                    ]
                )
            )
    return "\n\n".join(sections)


def build_note(
    repo_root: Path,
    batch_path: Path,
    batch_date: dt.date,
    kind: str,
    level: str,
    count: int,
    images: list[Path],
    title: str | None,
) -> str:
    template = load_template(repo_root)
    type_label = TYPE_LABELS.get(kind, kind)
    note_title = title or f"{level.upper()} {type_label}错题 {count} 题"
    asset_dir = repo_root / "mistakes" / "assets" / batch_date.isoformat()
    values = {
        "title": note_title,
        "level": level.lower(),
        "level_upper": level.upper(),
        "type_tag": kind,
        "type_label": type_label,
        "date": batch_date.isoformat(),
        "count": str(count),
        "asset_dir_label": f"mistakes/assets/{batch_date.isoformat()}",
        "asset_dir_link": markdown_link(batch_path, asset_dir),
        "image_list": image_markdown(repo_root, images),
        "overview_rows": overview_rows(count),
        "item_sections": item_sections(count, kind),
    }
    return template.format(**values)


def print_next_steps(
    repo_root: Path, batch_path: Path, batch_date: dt.date, kind: str, count: int
) -> None:
    type_label = TYPE_LABELS.get(kind, kind)
    print("\n下一步建议:")
    print(f"1. 补全 {batch_path}")
    print("2. 把批次加入 mistakes/README.md 的「批次列表」")
    print(f"3. 把批次加入 mistakes/by-type/ 对应题型索引")
    print("4. 如果有可复用知识点，新增或更新 grammar/、vocabulary/、kanji/、reading/ 下的主题笔记")
    print("\nmistakes/README.md 索引行草稿:")
    batch_link = wikilink(repo_root, batch_path, f"N2 {type_label}错题 {count} 题")
    print(
        f"| {batch_date.isoformat()} | {batch_link} |  |  |"
    )
    print("\n题型索引位置:")
    for index_dir in TYPE_INDEX_DIRS.get(kind, [kind]):
        index_file = repo_root / "mistakes" / "by-type" / index_dir / "README.md"
        type_link = wikilink(repo_root, batch_path, f"N2 {type_label}错题 {count} 题")
        print(f"- mistakes/by-type/{index_dir}/README.md: {type_link}")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    requested_date = validate_date(args.date) if args.date else None
    screenshots = find_screenshots(source_dir, requested_date)
    batch_date = infer_batch_date(args.date, screenshots)
    count = args.count if args.count is not None else len(screenshots)
    if count <= 0:
        raise SystemExit("题数必须大于 0。请使用 --count 指定题数。")

    asset_dir = repo_root / "mistakes" / "assets" / batch_date.isoformat()
    batch_path = make_batch_path(repo_root, batch_date, args.level, args.type, count)

    if batch_path.exists() and not args.force:
        raise SystemExit(f"批次文件已存在: {batch_path}\n如需覆盖，请加 --force。")

    moved_images = move_screenshots(screenshots, asset_dir, args.dry_run)
    note = build_note(
        repo_root=repo_root,
        batch_path=batch_path,
        batch_date=batch_date,
        kind=args.type,
        level=args.level,
        count=count,
        images=moved_images,
        title=args.title,
    )

    print(f"批次日期: {batch_date.isoformat()}")
    print(f"找到截图: {len(screenshots)}")
    for src, dest in zip(screenshots, moved_images):
        action = "将移动" if args.dry_run else "已移动"
        print(f"- {action}: {src} -> {dest}")

    if args.dry_run:
        print(f"\n将创建批次文件: {batch_path}")
    else:
        batch_path.parent.mkdir(parents=True, exist_ok=True)
        batch_path.write_text(note, encoding="utf-8")
        print(f"\n已创建批次文件: {batch_path}")

    print_next_steps(repo_root, batch_path, batch_date, args.type, count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
