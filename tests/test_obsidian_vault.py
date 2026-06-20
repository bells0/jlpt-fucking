import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ObsidianVaultTest(unittest.TestCase):
    def test_core_entrypoints_exist(self):
        self.assertTrue((ROOT / "学习首页.md").is_file())
        self.assertTrue((ROOT / "bases/知识点.base").is_file())
        self.assertTrue((ROOT / "bases/错题.base").is_file())
        self.assertTrue((ROOT / "templates/knowledge_point.md").is_file())

    def test_atomic_note_inventory(self):
        grammar = list((ROOT / "grammar").glob("文法-*.md"))
        vocabulary = list((ROOT / "vocabulary").glob("語彙-*.md"))
        kanji = list((ROOT / "kanji").glob("漢字-*.md"))
        self.assertGreaterEqual(len(grammar), 35)
        self.assertGreaterEqual(len(vocabulary), 12)
        self.assertGreaterEqual(len(kanji), 4)

    def test_vault_integrity_checker_passes(self):
        result = subprocess.run(
            [sys.executable, "scripts/check_obsidian_vault.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
