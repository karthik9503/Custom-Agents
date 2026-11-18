from langgraph.graph import END

from shorts.graph import after_validate, build_graph, start_router


def test_start_router():
    assert start_router({}) == "director"
    assert start_router({"raw_plan": "{}"}) == "validate"


def test_after_validate():
    assert after_validate({"error": None}) == "narrate"
    assert after_validate({"error": "bad", "attempts": 1}) == "director"
    assert after_validate({"error": "bad", "attempts": 3}) == END
    assert after_validate({"error": "bad", "attempts": 0, "plan_file": "p.json"}) == END


def test_retry_loop_gives_up_after_three(monkeypatch, run_dir):
    calls = []

    def fake_claude(prompt: str, timeout: int = 180) -> str:
        calls.append(prompt)
        return "not json"

    monkeypatch.setattr("shorts.llm.call_claude", fake_claude)
    final = build_graph().invoke({"transcript": "t", "run_dir": run_dir, "attempts": 0})

    assert len(calls) == 3
    assert final["attempts"] == 3
    assert final["error"]
    assert "failed validation" in calls[1]  # retries see the previous error


def test_graph_draws():
    mermaid = build_graph().get_graph().draw_mermaid()
    for node in ("director", "validate", "narrate", "render", "compose"):
        assert node in mermaid
