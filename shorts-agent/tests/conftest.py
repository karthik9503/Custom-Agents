import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from shorts.models import VideoPlan
from shorts.style import load_style

FIXTURE = Path(__file__).parent / "fixtures" / "plan_example.json"


@pytest.fixture
def plan_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def plan(plan_text) -> dict:
    # Validated, like the plan the render nodes get in a real run (defaults filled in).
    return VideoPlan.model_validate(json.loads(plan_text)).model_dump()


@pytest.fixture
def run_dir(tmp_path) -> str:
    return str(tmp_path)


@pytest.fixture
def fake_tts(monkeypatch):
    """Replace real TTS with silence as long as the words would take to speak."""
    wps = load_style()["timing"]["words_per_second"]

    def synthesize(text: str, out_path: Path) -> str:
        rate = 22050
        seconds = len(text.split()) / wps
        sf.write(str(out_path), np.zeros(int(rate * seconds), dtype="float32"), rate)
        return "fake"

    monkeypatch.setattr("shorts.tts.synthesize", synthesize)
