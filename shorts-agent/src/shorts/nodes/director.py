"""director: transcript -> raw VideoPlan JSON text. The only node that uses Claude."""

from pathlib import Path

from shorts import llm  # call through the module so tests can monkeypatch llm.call_claude
from shorts.state import ShortState
from shorts.style import ROOT

SKILLS_DIR = ROOT / ".claude" / "skills"


def read_skill(name: str) -> str:
    """Read a SKILL.md from disk, without its YAML frontmatter."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        _, _, text = text[3:].partition("---")
    return text.strip()


def build_prompt(transcript: str, error: str | None = None, previous: str | None = None) -> str:
    # Skills are passed explicitly; `claude -p` doesn't auto-load this repo's skills.
    parts = [
        read_skill("scene-director"),
        "# House style (follow it)\n\n" + read_skill("video-style"),
        "# Transcript\n\n" + transcript.strip(),
    ]
    if error:
        parts.append(
            "# Your previous answer failed validation\n\n"
            f"Previous answer:\n{previous}\n\nValidation error:\n{error}\n\n"
            "Fix exactly that and keep the rest."
        )
    parts.append("Respond with only the VideoPlan JSON object.")
    return "\n\n".join(parts)


def director(state: ShortState) -> dict:
    attempt = state.get("attempts", 0) + 1
    print(f"  asking Claude for a plan (attempt {attempt})...")
    prompt = build_prompt(state["transcript"], state.get("error"), state.get("raw_plan"))
    raw = llm.call_claude(prompt)

    # Keep every raw response for debugging.
    Path(state["run_dir"], f"director_attempt_{attempt}.txt").write_text(raw, encoding="utf-8")
    return {"raw_plan": raw, "attempts": attempt}
