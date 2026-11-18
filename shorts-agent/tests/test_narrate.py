from pathlib import Path

import pytest

from shorts.nodes.narrate import narrate, scene_durations

TIMING = {"min_total_s": 10, "max_total_s": 20, "min_scene_s": 2, "max_scene_s": 5,
          "pad_after_narration_s": 0.35}


def test_narrate_writes_audio(fake_tts, plan, run_dir):
    out = narrate({"plan": plan, "run_dir": run_dir})
    assert len(out["audio_paths"]) == len(plan["scenes"])
    assert all(Path(p).exists() for p in out["audio_paths"])
    # Fixture scene 1 has 7 words: 7 / 2.5 + 0.35 pad.
    assert abs(out["durations"][0] - 3.15) < 0.01


def test_durations_respect_minimums():
    assert scene_durations([3.0, 4.0, 4.0], TIMING) == pytest.approx([3.35, 4.35, 4.35])  # already >= 10 s
    d = scene_durations([0.5, 0.5], TIMING)
    assert d[0] == 2.0           # min_scene_s
    assert abs(sum(d) - 10) < 1e-9  # last scene held to reach min_total_s
