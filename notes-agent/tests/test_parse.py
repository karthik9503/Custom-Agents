"""Tests for turning model replies into tool calls or final answers."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from agent import build_system_prompt, parse_reply  # noqa: E402


class ParseReplyTests(unittest.TestCase):
    def test_tool_call(self) -> None:
        reply = '{"tool": "read_note", "args": {"name": "groceries"}}'
        self.assertEqual(parse_reply(reply), {"tool": "read_note", "args": {"name": "groceries"}})

    def test_tool_call_without_args(self) -> None:
        self.assertEqual(parse_reply('{"tool": "list_notes"}'), {"tool": "list_notes", "args": {}})

    def test_final(self) -> None:
        self.assertEqual(parse_reply('{"final": "You have 3 notes."}'),
                         {"final": "You have 3 notes."})

    def test_json_in_code_fences(self) -> None:
        reply = '```json\n{"tool": "list_notes", "args": {}}\n```'
        self.assertEqual(parse_reply(reply), {"tool": "list_notes", "args": {}})

    def test_json_with_chatter_around_it(self) -> None:
        reply = 'Sure! {"final": "Done."} Hope that helps.'
        self.assertEqual(parse_reply(reply), {"final": "Done."})

    def test_plain_text_is_error(self) -> None:
        self.assertIn("error", parse_reply("You have three notes."))

    def test_unknown_tool_is_error(self) -> None:
        result = parse_reply('{"tool": "delete_everything", "args": {}}')
        self.assertIn("unknown tool", result["error"])

    def test_args_must_be_object(self) -> None:
        self.assertIn("error", parse_reply('{"tool": "read_note", "args": "groceries"}'))

    def test_json_list_is_error(self) -> None:
        self.assertIn("error", parse_reply('[{"final": "hi"}]'))


class SystemPromptTests(unittest.TestCase):
    def test_tools_are_filled_in(self) -> None:
        prompt = build_system_prompt()
        self.assertNotIn("{{TOOLS}}", prompt)
        self.assertIn("- list_notes() ->", prompt)
        self.assertIn("- read_note(name) ->", prompt)


if __name__ == "__main__":
    unittest.main()
