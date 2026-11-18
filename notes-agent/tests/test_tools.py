"""Tests for the note tools, run against a temporary notes folder."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import tools  # noqa: E402


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        """Point the tools at a fresh temp folder so real notes are never touched."""
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.notes = self.root / "notes"
        self.notes.mkdir()
        patcher = mock.patch.object(tools, "NOTES_DIR", self.notes)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_list_notes_empty(self) -> None:
        self.assertEqual(tools.list_notes(), "No notes yet.")

    def test_list_notes_shows_names_without_extension(self) -> None:
        (self.notes / "groceries.md").write_text("milk", encoding="utf-8")
        (self.notes / "meeting.md").write_text("friday", encoding="utf-8")
        result = tools.list_notes()
        self.assertIn("groceries (modified", result)
        self.assertIn("meeting (modified", result)
        self.assertNotIn(".md", result)

    def test_read_note(self) -> None:
        (self.notes / "groceries.md").write_text("milk\neggs", encoding="utf-8")
        self.assertEqual(tools.read_note("groceries"), "milk\neggs")
        self.assertEqual(tools.read_note("groceries.md"), "milk\neggs")

    def test_read_missing_note_is_error(self) -> None:
        self.assertTrue(tools.read_note("diary").startswith("ERROR:"))

    def test_path_escape_is_rejected(self) -> None:
        (self.root / "secret.md").write_text("password", encoding="utf-8")
        for name in ["../secret", "..\\secret", "C:secret", "sub/note", ".."]:
            with self.subTest(name=name):
                result = tools.read_note(name)
                self.assertTrue(result.startswith("ERROR:"))
                self.assertNotIn("password", result)

    def test_bad_names_are_rejected(self) -> None:
        for name in ["", "   ", "x" * 51, 123, None]:
            with self.subTest(name=name):
                self.assertTrue(tools.read_note(name).startswith("ERROR:"))

    def test_every_tool_has_a_schema(self) -> None:
        self.assertEqual({s["name"] for s in tools.TOOL_SCHEMAS}, set(tools.TOOLS))


if __name__ == "__main__":
    unittest.main()
