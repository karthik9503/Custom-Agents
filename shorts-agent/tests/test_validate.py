from pathlib import Path

from shorts.nodes.validate import validate


def test_valid_plan(plan_text, run_dir):
    out = validate({"raw_plan": plan_text, "run_dir": run_dir})
    assert out["error"] is None
    assert len(out["plan"]["scenes"]) == 4
    assert Path(run_dir, "plan.json").exists()


def test_strips_fences(plan_text, run_dir):
    out = validate({"raw_plan": f"Here you go:\n```json\n{plan_text}\n```", "run_dir": run_dir})
    assert out["error"] is None


def test_invalid_plan_stores_error(run_dir):
    out = validate({"raw_plan": '{"title": "x", "scenes": []}', "run_dir": run_dir})
    assert out["plan"] is None
    assert "scenes" in out["error"]


def test_not_json(run_dir):
    out = validate({"raw_plan": "sorry, I can't do that", "run_dir": run_dir})
    assert out["error"]
