"""The agent's tools: functions that act on notes, plus their schemas for the model."""

import re
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path(__file__).resolve().parent.parent / "notes"
# Letters, numbers, -, _ and spaces, max 50 chars. This alone blocks /, \, .. and C:.
NAME_PATTERN = re.compile(r"[A-Za-z0-9 _-]{1,50}")


def note_path(name: str) -> Path:
    """Turn a note name into a safe path inside NOTES_DIR, or raise ValueError."""
    if not isinstance(name, str):
        raise ValueError("note name must be text")
    name = name.strip().removesuffix(".md")  # models often add ".md" anyway
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError(f"invalid note name '{name}'. Use letters, numbers, -, _ or "
                         "spaces, max 50 characters, no folders.")
    path = (NOTES_DIR / f"{name}.md").resolve()
    # Second line of defence: even if the name check had a gap, never leave notes/.
    if path.parent != NOTES_DIR.resolve():
        raise ValueError(f"note '{name}' is outside the notes folder")
    return path


def list_notes() -> str:
    """List every note with its last-modified date."""
    notes = sorted(NOTES_DIR.glob("*.md"))
    if not notes:
        return "No notes yet."
    lines = []
    for path in notes:
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"{path.stem} (modified {modified})")
    return "\n".join(lines)


def read_note(name: str) -> str:
    """Return the full text of one note."""
    try:
        path = note_path(name)
    except ValueError as error:
        return f"ERROR: {error}"
    if not path.exists():
        return f"ERROR: note '{name}' does not exist. Use list_notes to see all notes."
    return path.read_text(encoding="utf-8") or "(this note is empty)"


# One entry per tool, in the Anthropic API format. The CLI backend turns these into
# prompt text; a future API backend can send this list unchanged as `tools=`.
TOOL_SCHEMAS = [
    {
        "name": "list_notes",
        "description": "List the names of all notes with their last-modified dates.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_note",
        "description": "Return the full text of one note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Note name, e.g. groceries"},
            },
            "required": ["name"],
        },
    },
]

# Tool name -> the Python function that runs it.
TOOLS = {
    "list_notes": list_notes,
    "read_note": read_note,
}
