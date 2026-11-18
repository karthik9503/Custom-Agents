import numpy as np
import pytest

from shorts.render.action import DEMOS, _demo_frame_fn
from shorts.render.figure import render_figure
from shorts.render.moves import MOVE_POSES, MOVES, Step, Track, pose_named, rotate, swap_sides
from shorts.render.poses import POSES
from shorts.style import load_style

STYLE = load_style()
H = 300  # figure height for tests


def test_every_key_pose_exists():
    for name, move in MOVES.items():
        for key in move.keys:
            pose_named(key.pose)  # raises KeyError if missing
            assert key.ease in ("linear", "in", "out", "in_out", "back"), name


def test_move_poses_have_all_joints():
    joints = set(POSES["stand"])
    for name, pose in MOVE_POSES.items():
        assert set(pose) == joints, name


def test_keys_are_in_time_order():
    for name, move in MOVES.items():
        times = [k.t for k in move.keys]
        assert times == sorted(times) and times[0] > 0, name  # t>0: blend in from the previous move


def test_swap_sides_keeps_positions():
    pose = MOVE_POSES["run_contact"]
    swapped = swap_sides(pose)
    assert swapped["l_foot"] == pose["r_foot"] and swapped["head"] == pose["head"]


def test_rotate_around_hip():
    pose = POSES["stand"]
    turned = rotate(pose, 90)  # counter-clockwise: head swings to the left of the hip
    assert turned["hip"] == pose["hip"]
    assert turned["head"][0] < pose["hip"][0]
    assert turned["head"][1] == pytest.approx(pose["hip"][1])


def test_run_lands_exactly_on_target():
    track = Track(x=0, facing="right", height=H, steps=[Step("run", to_x=700)])
    _, x, y = track.state(track.end_time)
    assert x == pytest.approx(700) and y == 0
    # Speed: about cycle_dx heights per period.
    speed = 700 / track.end_time
    assert speed == pytest.approx(MOVES["run"].cycle_dx * H / MOVES["run"].period, rel=0.2)


def test_travel_turns_toward_target():
    track = Track(x=500, facing="right", height=H, steps=[Step("walk", to_x=100)])
    assert track.facing_at(track.end_time) == "left"


def test_jump_is_an_arc():
    track = Track(x=100, facing="right", height=H, steps=[Step("jump")])
    ys = [track.state(t)[2] for t in np.linspace(0, track.end_time, 60)]
    peak = int(np.argmax(ys))
    assert ys[0] == 0 and ys[-1] == 0 and max(ys) > 0.4 * H
    assert all(a <= b + 1e-6 for a, b in zip(ys[:peak], ys[1:peak + 1]))  # rises, then falls


def test_rising_slows_down_near_the_peak():
    # "out" easing: the first half of the rise covers more height than the second.
    track = Track(x=0, facing="right", height=H, steps=[Step("jump")])
    k = MOVES["jump"].keys
    t0, t1 = k[1].t, k[2].t                     # takeoff -> peak
    y0, ymid, y1 = (track.state(t)[2] for t in (t0, (t0 + t1) / 2, t1))
    assert ymid - y0 > y1 - ymid


def test_backflip_ends_upright():
    track = Track(x=500, facing="right", height=H, steps=[Step("backflip"), Step("jump")])
    after_flip = track.state(MOVES["backflip"].duration + 0.01)[0]
    assert after_flip["head"][1] > after_flip["hip"][1]     # head above hip again
    # The next move doesn't "unspin" 360 degrees: rotation stays small.
    mid_jump = track.state(MOVES["backflip"].duration + 0.3)[0]
    assert mid_jump["head"][1] > mid_jump["hip"][1]


def test_flop_turns_and_lies_down():
    track = Track(x=0, facing="right", height=H, steps=[Step("run", to_x=300), Step("flop")])
    pose, x, _ = track.state(track.end_time)
    assert track.facing_at(track.end_time) == "left"          # back to the bar
    assert abs(pose["head"][1] - pose["hip"][1]) < 0.05       # lying flat
    assert x > 300                                            # landed past the bar


def test_trails_only_on_marked_keys():
    track = Track(x=0, facing="right", height=H, steps=[Step("run", to_x=300), Step("flop")])
    run_end = [k.t for k in track.keys if k.trail][0]
    assert not track.trailing(0.1)                            # running: no trails
    assert track.trailing(run_end - 0.01)                     # flying over the bar: trails


def test_hold_between_steps():
    track = Track(x=0, facing="right", height=H, steps=[Step("jump"), Step("jump", at=3.0)])
    a, b = track.state(1.5), track.state(2.5)
    assert a[1] == b[1] and a[0] == b[0]                      # standing still in the gap


def test_upside_down_figure_renders():
    upside_down = rotate(POSES["stand"], 180)
    layer, (fx, fy) = render_figure(upside_down, H, STYLE, (0, 0, 0))
    # The head is now below the feet's origin, so the layer extends below it.
    assert layer.height > fy


@pytest.mark.parametrize("name", list(DEMOS))
def test_demo_frames(name):
    frame, _, track, _, duration = _demo_frame_fn(name, STYLE)
    first, mid = frame(0), frame(int(duration * STYLE["canvas"]["fps"] / 2))
    assert first.size == (STYLE["canvas"]["width"], STYLE["canvas"]["height"])
    assert np.asarray(first).tobytes() != np.asarray(mid).tobytes()


# --- Part 2: fighting ----------------------------------------------------------

from shorts.render.action import ActionScene, Actor, _sword_points  # noqa: E402
from shorts.render.moves import REACTIONS, side_joint  # noqa: E402


def test_side_joint_follows_mirroring():
    assert side_joint("r_hand", "right") == "r_hand"
    assert side_joint("r_hand", "left") == "l_hand"
    assert side_joint("head", "left") == "head"
    # The mirrored lead fist really is stored under the swapped name.
    pose = pose_named("punch", "left")
    assert pose[side_joint("r_hand", "left")][0] < 0.1


def test_every_strike_has_an_impact_and_reactions_exist():
    for name in ("punch", "kick", "slash"):
        assert sum(1 for k in MOVES[name].keys if k.impact) == 1, name
    assert set(REACTIONS) <= set(MOVES)


def _fight():
    frame, base, scene, ground, duration = _demo_frame_fn("fight", STYLE)
    return frame, scene, ground


def test_fight_impacts_match_reactions():
    _, scene, _ = _fight()
    # slash vs block (1), punch vs hit_react (2), slash vs knockback (3);
    # the kick is dodged, so it has no impact.
    assert sorted(i.strength for i in scene.impacts) == [1, 2, 3]
    assert len(scene.actors[1].track.impacts) == 2  # punch + kick were thrown


def test_punch_lands_on_the_body():
    _, scene, ground = _fight()
    a, b = scene.actors
    [punch] = [i for i in scene.impacts if i.strength == 2]
    body_x = a.track.state(punch.frame / STYLE["canvas"]["fps"])[1]
    assert abs(punch.x - body_x) < 0.15 * a.track.height        # fist reaches the chest
    assert ground - a.track.height < punch.y < ground - 0.4 * a.track.height


def test_shake_only_on_real_hits():
    _, scene, _ = _fight()
    by_strength = {i.strength: i for i in scene.impacts}
    assert scene._shake(by_strength[1].frame) == (0, 0)          # block: no shake
    assert scene._shake(by_strength[2].frame) != (0, 0)          # hit: shake
    assert scene._shake(0) == (0, 0)


def test_knockback_lands_on_screen():
    _, scene, ground = _fight()
    b = scene.actors[1].track
    pose, x, y = b.state(b.end_time)
    assert abs(pose["head"][1] - pose["hip"][1]) < 0.05          # lying down
    assert 0 < x < STYLE["canvas"]["width"]


def test_sword_follows_the_lead_forearm():
    t = Track(x=500, facing="left", height=H, steps=[Step("stance")])
    pose, x, y = t.state(t.end_time)
    pommel, _, _, tip = _sword_points(pose, x, y, 1000, H, STYLE, "left")
    assert tip[0] < pommel[0] and tip[1] < pommel[1]              # up and toward the left


def test_guard_bob_while_holding():
    t = Track(x=500, facing="right", height=H, steps=[Step("stance"), Step("punch", at=2.0)])
    assert t.holding(1.0) and not t.holding(2.1)
    scene = ActionScene([Actor(t, (0, 0, 0))], 1000, STYLE, (255, 255, 255), (255, 0, 0))
    heads = {round(scene._state(scene.actors[0], f)[0]["head"][1], 4) for f in range(10, 40)}
    assert len(heads) > 1                                         # it bounces
