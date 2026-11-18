import copy
import json
from pathlib import Path

import numpy as np
import pytest
from moviepy import VideoFileClip
from pydantic import ValidationError

from shorts import run
from shorts.models import Scene, VideoPlan
from shorts.nodes.narrate import narrate, scene_durations
from shorts.render.choreo import check_scene, scene_length
from shorts.render.scene import SceneRenderer
from shorts.style import load_style

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]
STYLE = load_style()


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def fight() -> dict:
    return VideoPlan.model_validate(load("plan_fight.json")).model_dump()


@pytest.fixture
def mixed() -> dict:
    return VideoPlan.model_validate(load("plan_mixed.json")).model_dump()


def test_fixtures_are_valid(fight, mixed):
    assert fight["audio_mode"] == "silent" and mixed["audio_mode"] == "mixed"
    for scene in fight["scenes"]:
        assert check_scene(scene) == []


# --- choreography checks: each error says how to fix it ------------------------------

def _errors(scene: dict) -> str:
    return " | ".join(check_scene(scene))


def test_strike_without_answer(fight):
    scene = copy.deepcopy(fight["scenes"][0])
    b = scene["characters"][1]
    b["moves"] = [m for m in b["moves"] if m["move"] != "block"]   # a's punch now hits air
    assert "nobody reacts" in _errors(scene) and '"at": 1.27' in _errors(scene)


def test_reaction_without_strike(fight):
    scene = copy.deepcopy(fight["scenes"][1])
    scene["characters"][1]["moves"][1]["at"] = 0.5                 # hit_react too early
    assert "has no strike to react to" in _errors(scene)


def test_strike_falls_short(fight):
    scene = copy.deepcopy(fight["scenes"][1])
    scene["characters"][1]["x"] = 0.75                             # too far away
    assert "falls short" in _errors(scene)


def test_overlapping_moves(fight):
    scene = copy.deepcopy(fight["scenes"][1])
    scene["characters"][0]["moves"][2]["at"] = 0.8                 # punch during the kick
    assert "starts before their previous move ends" in _errors(scene)


def test_off_screen():
    # Run to the right edge, then jump forward (+0.2 of the width): off the screen.
    scene = {"layout": "action", "props": [],
             "characters": [{"id": "a", "pose": "stand", "x": 0.6, "facing": "right", "color": "ink",
                             "holds": None, "moves": [{"move": "run", "at": 0.0, "to_x": 0.95},
                                                      {"move": "jump", "at": 1.0}]}]}
    assert "goes off-screen" in _errors(scene)


def test_fighters_overlap(fight):
    scene = copy.deepcopy(fight["scenes"][1])
    scene["characters"][1]["x"] = scene["characters"][0]["x"] + 0.05  # standing inside each other
    assert "overlap" in _errors(scene)


def test_facing_away(fight):
    scene = copy.deepcopy(fight["scenes"][1])
    scene["characters"][0]["facing"] = "left"                      # a turns its back on b
    assert "facing away" in _errors(scene)


def test_flop_needs_bar_at_crossing():
    scene = {"layout": "action", "props": [{"kind": "bar", "x": 0.3, "size": "large", "label": None}],
             "characters": [{"id": "a", "pose": "stand", "x": 0.15, "facing": "right", "color": "ink",
                             "holds": None, "moves": [{"move": "run", "at": 0.0, "to_x": 0.3},
                                                      {"move": "flop", "at": 0.5}]}]}
    assert "put the 'bar' at x" in _errors(scene)


# --- audio modes ---------------------------------------------------------------

def test_silent_scenes_only_in_action():
    with pytest.raises(ValidationError, match="only layout 'action' can be silent"):
        Scene.model_validate({"background": "white", "layout": "closeup",
                              "characters": [{"id": "a", "pose": "think"}]})


def test_narrated_mode_rejects_silent_scenes(fight):
    plan = load("plan_mixed.json") | {"audio_mode": "narrated"}
    with pytest.raises(ValidationError, match="every scene needs 'narration'"):
        VideoPlan.model_validate(plan)


def test_silent_mode_rejects_narration():
    plan = load("plan_mixed.json") | {"audio_mode": "silent"}
    with pytest.raises(ValidationError, match="no scene may have 'narration'"):
        VideoPlan.model_validate(plan)


def test_silent_needs_enough_action():
    plan = load("plan_fight.json")
    plan["scenes"] = plan["scenes"][:1]
    with pytest.raises(ValidationError, match="at least 8 s of action"):
        VideoPlan.model_validate(plan)


def test_action_fields_only_in_action_scenes():
    with pytest.raises(ValidationError, match="only used by layout 'action'"):
        Scene.model_validate({"narration": "x", "caption": "x", "background": "white", "layout": "closeup",
                              "characters": [{"id": "a", "pose": "think", "holds": "sword"}]})


def test_travel_needs_target():
    with pytest.raises(ValidationError, match="needs a 'to_x'"):
        Scene.model_validate({"background": "white", "layout": "action",
                              "characters": [{"id": "a", "pose": "stand", "moves": [{"move": "run", "at": 0}]}]})


# --- narrate, render, end to end -------------------------------------------------

def test_scene_durations_use_action_length():
    timing = STYLE["timing"]
    d = scene_durations([0.0, 2.0], timing, [6.5, 0.0])
    assert d[0] == 6.5                                   # silent: as long as its moves
    assert d[1] == pytest.approx(2.0 + timing["pad_after_narration_s"]) or sum(d) >= timing["min_total_s"]


def test_narrate_silent_scenes(fake_tts, mixed, run_dir):
    calls = []
    import shorts.tts as tts_module
    real = tts_module.synthesize

    def counting(text, path):
        calls.append(text)
        return real(text, path)

    tts_module.synthesize = counting
    try:
        out = narrate({"plan": mixed, "run_dir": run_dir})
    finally:
        tts_module.synthesize = real
    assert len(calls) == 2                               # only the narrated scenes
    assert out["durations"][1] == pytest.approx(scene_length(mixed["scenes"][1]))
    assert all(Path(p).exists() for p in out["audio_paths"])


def test_action_layout_renders(fight):
    scene = fight["scenes"][1]
    r = SceneRenderer(scene, scene_length(scene), STYLE)
    frames = [r.frame_at(t) for t in (0.0, 0.9, 2.0)]
    assert all(f.shape == (STYLE["canvas"]["height"], STYLE["canvas"]["width"], 3) for f in frames)
    assert not np.array_equal(frames[0], frames[1])      # they move
    assert r.caption_full is None                        # silent scene, no caption


def test_full_silent_run(fake_tts, monkeypatch, tmp_path):
    monkeypatch.setattr("shorts.llm.call_claude", lambda *a, **k: pytest.fail("--plan must not call Claude"))
    monkeypatch.setattr(run, "ROOT", tmp_path)
    code = run.main([str(ROOT / "input" / "fight.txt"), "--plan", str(FIXTURES / "plan_fight.json")])
    assert code == 0
    [video] = tmp_path.glob("output/*/short.mp4")
    with VideoFileClip(str(video)) as clip:
        assert 8 <= clip.duration <= 20
