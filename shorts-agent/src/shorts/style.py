"""Loads config/style.json, the single source of truth for the look."""

import json
from functools import lru_cache
from pathlib import Path

# src/shorts/style.py -> parents[2] is the project root (shorts-agent/).
ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = ROOT / "config" / "style.json"


@lru_cache(maxsize=1)
def load_style() -> dict:
    return json.loads(STYLE_PATH.read_text(encoding="utf-8"))


def project_path(relative: str) -> Path:
    """Resolve a path from style.json (e.g. a font) against the project root."""
    return ROOT / relative


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
