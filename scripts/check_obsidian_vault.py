#!/usr/bin/env python3
"""检查 Obsidian 知识库的属性、双链、嵌入和导航完整性。"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIRS = ("grammar", "vocabulary", "kanji", "mistakes", "plans")
ATOMIC_PREFIXES = ("文法-", "語彙-", "漢字-")
WIKILINK_RE = re.compile(r"!?\[\[([^\]]+)\]\]")
MARKDOWN_NOTE_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]*\.md(?:#[^)]*)?\)")


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if line and not line.startswith((" ", "-")) and ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def note_files() -> list[Path]:
    files = [ROOT / "README.md", ROOT / "学习首页.md"]
    for directory in CONTENT_DIRS:
        files.extend(sorted((ROOT / directory).rglob("*.md")))
    return [path for path in files if path.exists()]


def all_link_targets() -> tuple[set[str], dict[str, list[Path]]]:
    paths: set[str] = set()
    basenames: dict[str, list[Path]] = defaultdict(list)
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".obsidian" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        paths.add(relative.as_posix())
        basenames[path.stem].append(relative)
    return paths, basenames


def target_exists(target: str, paths: set[str], basenames: dict[str, list[Path]]) -> bool:
    clean = target.split("|", 1)[0].split("#", 1)[0].strip()
    if not clean or "{{" in clean:
        return True
    if clean in paths:
        return True
    if Path(clean).suffix.lower() in {
        ".md", ".base", ".png", ".jpg", ".jpeg", ".webp", ".pdf"
    }:
        return clean in paths
    if f"{clean}.md" in paths or f"{clean}.base" in paths:
        return True
    return len(basenames.get(Path(clean).name, [])) == 1


def check() -> list[str]:
    issues: list[str] = []
    required = [ROOT / "学习首页.md", ROOT / "bases/知识点.base", ROOT / "bases/错题.base"]
    for path in required:
        if not path.exists():
            issues.append(f"缺少入口文件: {path.relative_to(ROOT)}")

    paths, basenames = all_link_targets()
    incoming: dict[str, int] = defaultdict(int)
    for path in note_files():
        text = path.read_text(encoding="utf-8")
        props = frontmatter(text)
        for key in ("title", "type", "tags"):
            if key not in props:
                issues.append(f"{path.relative_to(ROOT)} 缺少属性 {key}")

        is_atomic = path.name.startswith(ATOMIC_PREFIXES)
        if is_atomic:
            for key in ("aliases", "level", "status", "sources"):
                if key not in props:
                    issues.append(f"{path.relative_to(ROOT)} 缺少知识点属性 {key}")
            if props.get("status") not in {"待学习", "复习中", "已掌握"}:
                issues.append(f"{path.relative_to(ROOT)} 的 status 不合法")

        if "mistakes" in path.parts and re.match(r"^20\d{2}-\d{2}-\d{2}-", path.name):
            for key in ("level", "date", "question_type", "item_count"):
                if key not in props:
                    issues.append(f"{path.relative_to(ROOT)} 缺少错题属性 {key}")

        if MARKDOWN_NOTE_LINK_RE.search(text):
            issues.append(f"{path.relative_to(ROOT)} 仍含指向 .md 的普通 Markdown 链接")

        for match in WIKILINK_RE.finditer(text):
            target = match.group(1)
            if not target_exists(target, paths, basenames):
                issues.append(f"{path.relative_to(ROOT)} 含失效双链: [[{target}]]")
            clean = target.split("|", 1)[0].split("#", 1)[0].strip()
            suffix = Path(clean).suffix.lower()
            key = Path(clean).stem if suffix in {".md", ".base"} else Path(clean).name
            incoming[key] += 1

    for prefix, directory in (("文法-", "grammar"), ("語彙-", "vocabulary"), ("漢字-", "kanji")):
        for path in (ROOT / directory).glob(f"{prefix}*.md"):
            if incoming[path.stem] == 0:
                issues.append(f"孤立知识点: {path.relative_to(ROOT)}")
    return issues


def main() -> int:
    issues = check()
    if issues:
        print("Obsidian 知识库检查未通过：")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Obsidian 知识库检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
