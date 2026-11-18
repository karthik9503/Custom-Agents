from pathlib import Path

from shorts.nodes.director import build_prompt, director


def test_director_saves_raw_response(monkeypatch, plan_text, run_dir):
    prompts = []

    def fake_claude(prompt: str, timeout: int = 180) -> str:
        prompts.append(prompt)
        return plan_text

    monkeypatch.setattr("shorts.llm.call_claude", fake_claude)
    out = director({"transcript": "Why do we yawn?", "run_dir": run_dir})

    assert out == {"raw_plan": plan_text, "attempts": 1}
    assert Path(run_dir, "director_attempt_1.txt").read_text(encoding="utf-8") == plan_text
    assert "Why do we yawn?" in prompts[0]


def test_prompt_includes_skills_and_error():
    prompt = build_prompt("A transcript.", error="x must be >= 0.15", previous='{"title": "t"}')
    assert "# Scene director" in prompt   # scene-director skill
    assert "Video style" in prompt        # video-style skill
    assert "---" not in prompt.splitlines()[0]  # frontmatter stripped
    assert "x must be >= 0.15" in prompt
    assert '{"title": "t"}' in prompt


def test_prompt_without_error_has_no_retry_section():
    assert "failed validation" not in build_prompt("A transcript.")
