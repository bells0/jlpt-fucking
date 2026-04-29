#!/usr/bin/env python3
"""检查错题笔记是否先完整保留原题。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ITEM_HEADING_RE = re.compile(r"^###\s+(\d+|\d+-\d+)\b", re.MULTILINE)
STOP_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 mistakes 下的错题原题记录结构。")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["mistakes"],
        help="要检查的文件或目录，默认检查 mistakes。",
    )
    return parser.parse_args()


def iter_markdown(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.glob("20*/*/*.md")))
        elif path.is_file() and path.suffix == ".md":
            files.append(path)
    return files


def item_sections(text: str) -> list[tuple[str, str]]:
    start_marker = text.find("## 逐题整理")
    if start_marker == -1:
        start_marker = text.find("## 错题解析")
    if start_marker == -1:
        return []
    next_major = STOP_HEADING_RE.search(text, start_marker + 1)
    while next_major and next_major.group(0).startswith("## ") and next_major.start() == start_marker:
        next_major = STOP_HEADING_RE.search(text, next_major.end())
    scoped_text = text[start_marker : next_major.start() if next_major else len(text)]
    matches = list(ITEM_HEADING_RE.finditer(scoped_text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        next_item = matches[index + 1].start() if index + 1 < len(matches) else len(scoped_text)
        stop = STOP_HEADING_RE.search(scoped_text, match.end(), next_item)
        end = stop.start() if stop else next_item
        sections.append((match.group(0), scoped_text[start:end]))
    return sections


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    for heading, section in item_sections(text):
        if "#### 原题完整记录（不要加工）" not in section:
            issues.append(f"{path}: {heading} 缺少「原题完整记录（不要加工）」")
        if "选项" not in section:
            issues.append(f"{path}: {heading} 缺少选项记录")
        if "你的答案" not in section:
            issues.append(f"{path}: {heading} 缺少你的答案记录")
        if "正解" not in section:
            issues.append(f"{path}: {heading} 缺少正解记录")
    return issues


def main() -> int:
    args = parse_args()
    files = iter_markdown(args.paths)
    all_issues: list[str] = []
    for path in files:
        all_issues.extend(check_file(path))
    if all_issues:
        print("错题原题记录检查未通过：")
        for issue in all_issues:
            print(f"- {issue}")
        return 1
    print("错题原题记录检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
