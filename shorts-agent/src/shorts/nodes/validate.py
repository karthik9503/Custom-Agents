"""validate: parse the raw plan with Pydantic; store the error for a retry."""

import json
from pathlib import Path

from pydantic import ValidationError

from shorts.models import VideoPlan
from shorts.state import ShortState


def clean_json(raw: str) -> str:
    """Strip accidental ``` fences or chatter around the JSON object."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return raw.strip()
    return raw[start : end + 1]


def validate(state: ShortState) -> dict:
    raw = clean_json(state.get("raw_plan", ""))
    try:
        plan = VideoPlan.model_validate_json(raw)
    except ValidationError as e:
        print(f"  plan invalid: {e.error_count()} error(s)")
        return {"plan": None, "error": str(e)}

    data = plan.model_dump()
    Path(state["run_dir"], "plan.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"plan": data, "error": None}
