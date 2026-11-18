from pathlib import Path

import numpy as np
import pytest
from moviepy import VideoFileClip

from shorts.models import Pose, Scene
from shorts.nodes.render import render
from shorts.render.captions import parse_caption
from shorts.render.layouts import format_number
from shorts.render.motion import ease_out_back, lerp_pose
from shorts.render.poses import POSES, get_pose, write_contact_sheet
from shorts.render.scene import SceneRenderer
from shorts.render.sheets import SAMPLE_SCENES, write_layout_sheet, write_prop_sheet
from shorts.style import load_style

STYLE = load_style()
SHAPE = (STYLE["canvas"]["height"], STYLE["canvas"]["width"], 3)


def test_every_pose_exists():
    assert set(Pose.__args__) == set(POSES)


def test_facing_left_mirrors():
    right, left = get_pose("point", "right"), get_pose("point", "left")
    assert right["r_hand"][0] > 0.5 and left["l_hand"][0] < 0.5


def test_parse_caption_marks_accent():
    words = parse_caption("Why do we *yawn*?")
    assert words[-1] == [("yawn", True), ("?", False)]
    assert all(not accent for w in words[:-1] for _, accent in w)


def test_format_number():
    assert format_number(450, 450) == "450"
    assert format_number(1_500_000, 1_500_000) == "1,500,000"
    assert format_number(3.5, 3.5) == "3.5"
    assert format_number(225.4, 450) == "225"  # counting up keeps the target's format


def test_motion_helpers():
    assert ease_out_back(0) == pytest.approx(0) and ease_out_back(1) == pytest.approx(1)
    assert max(ease_out_back(p / 20) for p in range(21)) > 1  # the pop overshoots
    a, b = get_pose("stand"), get_pose("cheer")
    assert lerp_pose(a, b, 0) == a and lerp_pose(a, b, 1) == b


# --- one renderer per layout ---------------------------------------------------

def _renderer(layout: str, duration: float = 2.0) -> SceneRenderer:
    [sample] = [s for s in SAMPLE_SCENES if s["layout"] == layout]
    return SceneRenderer(Scene.model_validate(sample).model_dump(), duration, STYLE)


@pytest.mark.parametrize("layout", ["dialogue", "closeup", "big_number", "versus", "timeline"])
def test_layout_renders_and_animates(layout):
    # Each sample scene has an action (timeline animates on its own), so the
    # first and last frames must differ beyond the caption pop-in.
    r = _renderer(layout)
    first = r.frame_at(0.0)
    last = r.frame_at(r.duration)
    assert first.shape == last.shape == SHAPE
    below_caption = int(r.caption_bottom) + 1
    assert not np.array_equal(first[below_caption:], last[below_caption:])


def test_layout_draws_something_below_caption():
    # Guard against a layout that silently draws nothing: compare to a blank background.
    for layout in ("closeup", "big_number", "versus", "timeline"):
        r = _renderer(layout)
        frame = r.frame_at(r.duration)
        blank = np.asarray(r.base)
        below = int(r.caption_bottom) + 1
        assert not np.array_equal(frame[below:], blank[below:]), layout


def test_count_up_ends_on_the_number():
    r = _renderer("big_number")
    early, end = r.frame_at(0.1), r.frame_at(r.duration)
    # The end frame matches a scene with no count-up (the number is final).
    static = SceneRenderer({**r.scene, "action": "none"}, r.duration, STYLE).frame_at(r.duration)
    assert np.array_equal(end, static)
    assert not np.array_equal(early, static)


def test_bubble_waits_for_enter_left(plan):
    r = SceneRenderer(plan["scenes"][2], 2.0, STYLE)  # dialogue + enter_left + bubble
    assert r.entering(0.0) == 0 and r.entering(r.duration) == 1
    r.frame_at(0.0)
    assert ("bubble", "b") not in r._memo  # still walking in: no bubble yet
    r.frame_at(r.duration)
    assert ("bubble", "b") in r._memo      # arrived: the speaker's bubble is drawn


def test_render_node(plan, run_dir):
    durations = [0.5] * len(plan["scenes"])  # short clips keep the test fast
    out = render({"plan": plan, "durations": durations, "run_dir": run_dir, "debug": True})
    assert len(out["clip_paths"]) == len(plan["scenes"])
    with VideoFileClip(out["clip_paths"][0]) as clip:
        assert clip.size == [1080, 1920]
    assert Path(run_dir, "debug", "scene_00.png").exists()


def test_contact_sheets(tmp_path):
    for write, name in ((write_contact_sheet, "poses.png"), (write_prop_sheet, "props.png"),
                        (write_layout_sheet, "layouts.png")):
        write(tmp_path / name)
        assert (tmp_path / name).exists()
