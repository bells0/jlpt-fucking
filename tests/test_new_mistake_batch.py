import datetime as dt
import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "new_mistake_batch", ROOT / "scripts" / "new_mistake_batch.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class NewMistakeBatchObsidianTest(unittest.TestCase):
    def make_repo(self, base: Path) -> Path:
        repo = base / "repo"
        (repo / "templates").mkdir(parents=True)
        (repo / "templates" / "mistake_batch.md").write_text(
            (ROOT / "templates" / "mistake_batch.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return repo

    def test_build_note_contains_properties_and_obsidian_embeds(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            repo = Path(raw_dir)
            (repo / "templates").mkdir()
            (repo / "templates" / "mistake_batch.md").write_text(
                (ROOT / "templates" / "mistake_batch.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            batch = repo / "mistakes/2026/06/2026-06-20-n2-bunpou-01-items.md"
            image = repo / "mistakes/assets/2026-06-20/Screenshot_20260620_120000.png"

            note = MODULE.build_note(
                repo_root=repo,
                batch_path=batch,
                batch_date=dt.date(2026, 6, 20),
                kind="bunpou",
                level="n2",
                count=1,
                images=[image],
                title=None,
            )

        self.assertTrue(note.startswith("---\n"))
        self.assertIn("title: N2 文法错题 1 题", note)
        self.assertIn("type: 错题", note)
        self.assertIn("level: N2", note)
        self.assertIn("date: 2026-06-20", note)
        self.assertIn("question_type: 文法", note)
        self.assertIn("item_count: 1", note)
        self.assertIn("![[mistakes/assets/2026-06-20/Screenshot_20260620_120000.png]]", note)

    def test_dry_run_does_not_create_batch(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            base = Path(raw_dir)
            repo = self.make_repo(base)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/new_mistake_batch.py"),
                    "--date", "2026-06-20",
                    "--type", "bunpou",
                    "--count", "1",
                    "--source-dir", str(base),
                    "--repo-root", str(repo),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
            )
            batch = repo / "mistakes/2026/06/2026-06-20-n2-bunpou-01-items.md"
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(batch.exists())
            self.assertIn("将创建批次文件", result.stdout)

    def test_no_screenshot_batch_is_created_and_duplicate_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            base = Path(raw_dir)
            repo = self.make_repo(base)
            command = [
                sys.executable,
                str(ROOT / "scripts/new_mistake_batch.py"),
                "--date", "2026-06-20",
                "--type", "goi",
                "--count", "2",
                "--source-dir", str(base),
                "--repo-root", str(repo),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            second = subprocess.run(command, capture_output=True, text=True)
            batch = repo / "mistakes/2026/06/2026-06-20-n2-goi-02-items.md"
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertTrue(batch.exists())
            self.assertIn("question_type: 語彙", batch.read_text(encoding="utf-8"))
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("批次文件已存在", second.stderr)

    def test_all_supported_types_have_display_labels(self):
        self.assertEqual(set(MODULE.TYPE_LABELS), set(MODULE.TYPE_INDEX_DIRS))
        for kind, label in MODULE.TYPE_LABELS.items():
            self.assertTrue(kind)
            self.assertTrue(label)

    def test_index_draft_uses_wikilink(self):
        output = io.StringIO()
        batch = ROOT / "mistakes/2026/06/2026-06-20-n2-bunpou-01-items.md"
        with contextlib.redirect_stdout(output):
            MODULE.print_next_steps(ROOT, batch, dt.date(2026, 6, 20), "bunpou", 1)
        self.assertIn(
            "[[mistakes/2026/06/2026-06-20-n2-bunpou-01-items|N2 文法错题 1 题]]",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
