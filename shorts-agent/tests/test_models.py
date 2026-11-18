import copy
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from shorts.models import (ACTION_MOVES, ACTIONS, AUDIO_MODES, LAYOUT_LIMITS, LAYOUTS, PROP_KINDS,
                           TRAVEL_MOVES, Scene, VideoPlan)
from shorts.render.moves import MOVES
from shorts.render.layouts import LAYOUT_RENDERERS
from shorts.render.props import PROP_DRAWERS

SKILL = (Path(__file__).resolve().parents[1] / ".claude" / "skills" / "scene-director" / "SKILL.md"
         ).read_text(encoding="utf-8")


def test_fixture_is_valid(plan):
    VideoPlan.model_validate(plan)


# --- the original rules ------------------------------------------------------

@pytest.mark.parametrize("mutate, message", [
    (lambda p: p["scenes"][2]["characters"][1].update(x=0.4), "apart"),
    (lambda p: p["scenes"][2]["characters"][0].update(says="Hi"), "bubble"),
    (lambda p: p["scenes"][0]["characters"][0].update(pose="dance"), "pose"),
    (lambda p: p["scenes"][0].update(caption="one two three four five six seven"), "1-6 words"),
    (lambda p: p["scenes"][0].update(caption="*two* *stars*"), "at most one"),
    (lambda p: p["scenes"][0].update(narration="word " * 40), "total narration"),
    (lambda p: p.update(scenes=p["scenes"][:1]), "at least 3"),
])
def test_invalid_plans(plan, mutate, message):
    bad = copy.deepcopy(plan)
    mutate(bad)
    with pytest.raises(ValidationError, match=message):
        VideoPlan.model_validate(bad)


# --- Milestone 5: video-level variety ----------------------------------------

def test_same_layout_twice_in_a_row(plan):
    bad = copy.deepcopy(plan)
    # closeup, versus, dialogue, closeup -> closeup, versus, dialogue, dialogue
    bad["scenes"][3].update(layout="dialogue")
    with pytest.raises(ValidationError, match="scenes 2 and 3 both use layout 'dialogue'"):
        VideoPlan.model_validate(bad)


def test_needs_three_layouts(plan):
    bad = copy.deepcopy(plan)
    bad["scenes"][2] = copy.deepcopy(bad["scenes"][1])  # closeup, versus, versus, closeup
    bad["scenes"][2]["narration"] = plan["scenes"][2]["narration"]
    with pytest.raises(ValidationError, match="at least 3 different layouts"):
        VideoPlan.model_validate(bad)


# --- Milestone 5: scene rules --------------------------------------------------

def scene(**fields) -> dict:
    base = {"narration": "Some words here.", "caption": "A caption", "background": "white"}
    return base | fields


FIGURE = {"id": "a", "pose": "stand"}
PROP = {"kind": "tree"}


@pytest.mark.parametrize("fields, message", [
    # layout limits
    (dict(layout="closeup", characters=[]), "exactly 1 characters"),
    (dict(layout="closeup", characters=[FIGURE], props=[PROP]), "exactly 0 props"),
    (dict(layout="versus", props=[PROP]), "exactly 2 props"),
    (dict(layout="timeline", props=[PROP]), "2-3 props"),
    (dict(layout="versus", props=[{"kind": "tree", "label": "A"}, PROP]), "'label' on both"),
    (dict(layout="big_number"), "needs a 'number'"),
    (dict(layout="dialogue", number=3), "only used by layout 'big_number'"),
    (dict(layout="big_number", number=3, characters=[FIGURE | {"says": "Hi"}]), "bubbles only fit"),
    # actions
    (dict(layout="dialogue", action="pose_change", characters=[FIGURE]), "needs a character with an 'end_pose'"),
    (dict(layout="dialogue", action="pose_change", characters=[FIGURE | {"end_pose": "stand"}]), "must differ"),
    (dict(layout="dialogue", characters=[FIGURE | {"end_pose": "jump"}]), "only allowed with action"),
    (dict(layout="dialogue", action="enter_left"), "needs at least one character"),
    (dict(layout="dialogue", action="pop", characters=[FIGURE]), "needs at least one prop"),
    (dict(layout="dialogue", action="count_up"), "only works with layout 'big_number'"),
    # props
    (dict(layout="dialogue", props=[{"kind": "dragon"}]), "'shark'"),
    (dict(layout="dialogue", characters=[FIGURE | {"x": 0.2}],
          props=[{"kind": "tree", "x": 0.45, "size": "large"}]), "at least 0.3 apart"),
])
def test_invalid_scenes(fields, message):
    with pytest.raises(ValidationError, match=re.escape(message)):
        Scene.model_validate(scene(**fields))


@pytest.mark.parametrize("fields", [
    dict(layout="big_number", action="count_up", number=450, unit="million years"),
    dict(layout="timeline", props=[PROP, {"kind": "shark"}, {"kind": "star"}]),
    dict(layout="closeup", action="pose_change", characters=[FIGURE | {"end_pose": "jump", "says": "Whoa!"}]),
    dict(layout="dialogue", action="pop", characters=[FIGURE | {"x": 0.2}],
         props=[{"kind": "tree", "x": 0.5, "size": "large"}]),
])
def test_valid_scenes(fields):
    Scene.model_validate(scene(**fields))


# --- catalogs stay in sync -----------------------------------------------------

def test_catalogs_match_renderer():
    assert set(PROP_KINDS) == set(PROP_DRAWERS)
    assert set(LAYOUTS) == set(LAYOUT_RENDERERS) == set(LAYOUT_LIMITS)
    assert set(ACTION_MOVES) == set(MOVES)
    assert set(TRAVEL_MOVES) == {name for name, m in MOVES.items() if m.is_travel}


@pytest.mark.parametrize("name", [*PROP_KINDS, *LAYOUTS, *ACTIONS, *ACTION_MOVES, *AUDIO_MODES])
def test_skill_lists_every_value(name):
    # The director only knows about values the skill tells it about.
    assert name in SKILL


def test_skill_examples_are_valid():
    examples = re.findall(r"```json\n(\{.*?\})\n```", SKILL, re.S)[1:]  # [0] is the schema
    assert len(examples) >= 3
    layouts, modes = set(), set()
    for example in examples:
        plan = VideoPlan.model_validate_json(example)
        layouts |= {s.layout for s in plan.scenes}
        modes.add(plan.audio_mode)
    # Together the examples show every layout and every audio mode.
    assert layouts == set(LAYOUTS) and modes == set(AUDIO_MODES)
