"""Move library: timed keyframes that make figures run, jump and flip.

A Move is a list of Keys. Each Key says *when* (seconds after the move starts),
*which pose*, *where* the body is (forward travel `dx` and height `dy`, both in
figure heights) and how far it is *rotated* (`rot`, degrees, + leans backward).
Its `ease` shapes how the body gets there from the previous key; that's where
the smoothness comes from (anticipation and follow-through are just extra keys).

A Track chains moves for one character and answers "where is everybody at t?".

Run `python -m shorts.render.moves --demo fosbury` for an onion-skin sheet and a
short clip of the Fosbury flop.
"""

import argparse
import math
from bisect import bisect_right
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from shorts.render.motion import ease_in_out, ease_out_back, lerp, lerp_pose
from shorts.render.poses import POSES, PoseDict, mirror

EASES: dict[str, Callable[[float], float]] = {
    "linear": lambda p: p,
    "in": lambda p: p * p,              # speeds up (falling)
    "out": lambda p: 1 - (1 - p) ** 2,  # slows down (rising, settling)
    "in_out": ease_in_out,
    "back": ease_out_back,              # overshoots, then settles (snappy hits)
}

# Poses used only inside moves (the plan's `pose` field can't pick them).
# Same unit box as poses.py: y up, origin at the feet, figure facing right.
MOVE_POSES: dict[str, PoseDict] = {
    # Run: right leg reaching forward, left pushing off; arms swing opposite.
    "run_contact": {"head": (0.60, 0.85), "neck": (0.56, 0.73), "hip": (0.50, 0.44),
                    "l_elbow": (0.64, 0.58), "l_hand": (0.72, 0.68),
                    "r_elbow": (0.42, 0.56), "r_hand": (0.35, 0.47),
                    "l_knee": (0.42, 0.24), "l_foot": (0.27, 0.15),
                    "r_knee": (0.63, 0.26), "r_foot": (0.73, 0.04)},
    # Run: right leg under the body, left knee driving forward. Body a bit higher.
    "run_pass": {"head": (0.60, 0.88), "neck": (0.56, 0.76), "hip": (0.50, 0.47),
                 "l_elbow": (0.55, 0.60), "l_hand": (0.61, 0.53),
                 "r_elbow": (0.49, 0.60), "r_hand": (0.53, 0.50),
                 "l_knee": (0.65, 0.36), "l_foot": (0.51, 0.22),
                 "r_knee": (0.55, 0.24), "r_foot": (0.50, 0.0)},
    "walk_pass": {"head": (0.52, 0.87), "neck": (0.51, 0.74), "hip": (0.50, 0.43),
                  "l_elbow": (0.51, 0.58), "l_hand": (0.54, 0.45),
                  "r_elbow": (0.49, 0.58), "r_hand": (0.46, 0.45),
                  "l_knee": (0.61, 0.26), "l_foot": (0.51, 0.08),
                  "r_knee": (0.51, 0.22), "r_foot": (0.50, 0.0)},
    # Anticipation before a jump: knees bent, arms swung back.
    "crouch": {"head": (0.60, 0.70), "neck": (0.57, 0.59), "hip": (0.47, 0.30),
               "l_elbow": (0.40, 0.48), "l_hand": (0.30, 0.40),
               "r_elbow": (0.42, 0.46), "r_hand": (0.33, 0.36),
               "l_knee": (0.62, 0.18), "l_foot": (0.45, 0.0),
               "r_knee": (0.66, 0.16), "r_foot": (0.55, 0.0)},
    # Leaving the ground: push leg straight, other knee driving up, arms up.
    "takeoff": {"head": (0.54, 0.92), "neck": (0.53, 0.80), "hip": (0.50, 0.48),
                "l_elbow": (0.62, 0.90), "l_hand": (0.68, 1.04),
                "r_elbow": (0.60, 0.88), "r_hand": (0.64, 1.02),
                "l_knee": (0.47, 0.25), "l_foot": (0.44, 0.02),
                "r_knee": (0.62, 0.36), "r_foot": (0.58, 0.18)},
    # Flip: knees pulled up, shins down, hands reaching for the knees. Open enough
    # that the body still reads as a figure while it spins.
    "tuck": {"head": (0.58, 0.82), "neck": (0.54, 0.71), "hip": (0.47, 0.47),
             "l_elbow": (0.62, 0.62), "l_hand": (0.70, 0.56),
             "r_elbow": (0.64, 0.60), "r_hand": (0.72, 0.54),
             "l_knee": (0.68, 0.62), "l_foot": (0.62, 0.38),
             "r_knee": (0.70, 0.58), "r_foot": (0.64, 0.35)},
    # Landing: knees absorb, arms forward for balance (follow-through).
    "land": {"head": (0.58, 0.72), "neck": (0.55, 0.61), "hip": (0.47, 0.32),
             "l_elbow": (0.64, 0.58), "l_hand": (0.74, 0.56),
             "r_elbow": (0.66, 0.56), "r_hand": (0.76, 0.54),
             "l_knee": (0.60, 0.19), "l_foot": (0.42, 0.0),
             "r_knee": (0.64, 0.17), "r_foot": (0.56, 0.0)},
    # Fosbury flop: back arched, hips pushed forward, head and feet trailing.
    "arch": {"head": (0.36, 0.84), "neck": (0.42, 0.72), "hip": (0.58, 0.44),
             "l_elbow": (0.34, 0.64), "l_hand": (0.24, 0.66),
             "r_elbow": (0.36, 0.62), "r_hand": (0.26, 0.62),
             "l_knee": (0.50, 0.22), "l_foot": (0.34, 0.10),
             "r_knee": (0.52, 0.20), "r_foot": (0.36, 0.08)},
    # Lying on the back (once rotated 90 degrees): knees up, hands on the belly.
    "lie": {"head": (0.5, 0.86), "neck": (0.5, 0.73), "hip": (0.5, 0.42),
            "l_elbow": (0.58, 0.62), "l_hand": (0.60, 0.50),
            "r_elbow": (0.60, 0.64), "r_hand": (0.62, 0.52),
            "l_knee": (0.66, 0.26), "l_foot": (0.56, 0.06),
            "r_knee": (0.68, 0.24), "r_foot": (0.58, 0.04)},
    # Fosbury flop: legs flick up and forward to clear the bar.
    "pike": {"head": (0.44, 0.85), "neck": (0.46, 0.72), "hip": (0.50, 0.42),
             "l_elbow": (0.36, 0.60), "l_hand": (0.30, 0.48),
             "r_elbow": (0.38, 0.58), "r_hand": (0.32, 0.46),
             "l_knee": (0.70, 0.50), "l_foot": (0.88, 0.60),
             "r_knee": (0.72, 0.48), "r_foot": (0.90, 0.56)},

    # --- Fighting. "r_" is the lead side (toward the opponent), "l_" the rear. ---
    # Guard: knees bent, feet apart, fists up; lead fist forward.
    "stance": {"head": (0.54, 0.83), "neck": (0.52, 0.71), "hip": (0.49, 0.41),
               "l_elbow": (0.58, 0.56), "l_hand": (0.64, 0.67),
               "r_elbow": (0.66, 0.58), "r_hand": (0.72, 0.69),
               "l_knee": (0.40, 0.21), "l_foot": (0.33, 0.0),
               "r_knee": (0.61, 0.22), "r_foot": (0.67, 0.0)},
    # Wind-up: lead fist pulled back, torso coiled.
    "punch_wind": {"head": (0.51, 0.83), "neck": (0.50, 0.71), "hip": (0.48, 0.41),
                   "l_elbow": (0.57, 0.56), "l_hand": (0.63, 0.67),
                   "r_elbow": (0.50, 0.56), "r_hand": (0.58, 0.64),
                   "l_knee": (0.40, 0.21), "l_foot": (0.33, 0.0),
                   "r_knee": (0.61, 0.22), "r_foot": (0.67, 0.0)},
    "punch": {"head": (0.62, 0.82), "neck": (0.58, 0.71), "hip": (0.50, 0.41),
              "l_elbow": (0.58, 0.55), "l_hand": (0.64, 0.66),
              "r_elbow": (0.77, 0.69), "r_hand": (0.96, 0.71),
              "l_knee": (0.40, 0.20), "l_foot": (0.30, 0.0),
              "r_knee": (0.66, 0.22), "r_foot": (0.72, 0.0)},
    "kick_chamber": {"head": (0.50, 0.84), "neck": (0.49, 0.72), "hip": (0.48, 0.44),
                     "l_elbow": (0.40, 0.58), "l_hand": (0.36, 0.68),
                     "r_elbow": (0.60, 0.60), "r_hand": (0.66, 0.70),
                     "l_knee": (0.47, 0.22), "l_foot": (0.46, 0.0),
                     "r_knee": (0.66, 0.52), "r_foot": (0.62, 0.32)},
    # Side kick: lead leg straight out at hip height, torso leaning away.
    "kick": {"head": (0.36, 0.80), "neck": (0.40, 0.69), "hip": (0.50, 0.45),
             "l_elbow": (0.30, 0.60), "l_hand": (0.22, 0.56),
             "r_elbow": (0.50, 0.62), "r_hand": (0.58, 0.70),
             "l_knee": (0.46, 0.22), "l_foot": (0.44, 0.0),
             "r_knee": (0.74, 0.49), "r_foot": (0.98, 0.53)},
    # Forearms up in front of the face, leaning back a little.
    "block": {"head": (0.48, 0.83), "neck": (0.48, 0.71), "hip": (0.49, 0.41),
              "l_elbow": (0.62, 0.62), "l_hand": (0.60, 0.88),
              "r_elbow": (0.66, 0.64), "r_hand": (0.66, 0.90),
              "l_knee": (0.40, 0.21), "l_foot": (0.33, 0.0),
              "r_knee": (0.61, 0.22), "r_foot": (0.67, 0.0)},
    # Lean far back away from the attack.
    "dodge": {"head": (0.30, 0.66), "neck": (0.37, 0.58), "hip": (0.52, 0.36),
              "l_elbow": (0.30, 0.46), "l_hand": (0.22, 0.40),
              "r_elbow": (0.44, 0.68), "r_hand": (0.52, 0.78),
              "l_knee": (0.48, 0.18), "l_foot": (0.38, 0.0),
              "r_knee": (0.68, 0.22), "r_foot": (0.74, 0.0)},
    # Sword raised up and back.
    "slash_wind": {"head": (0.50, 0.84), "neck": (0.49, 0.72), "hip": (0.48, 0.42),
                   "l_elbow": (0.58, 0.58), "l_hand": (0.64, 0.66),
                   "r_elbow": (0.44, 0.86), "r_hand": (0.40, 1.00),
                   "l_knee": (0.40, 0.21), "l_foot": (0.33, 0.0),
                   "r_knee": (0.61, 0.22), "r_foot": (0.67, 0.0)},
    # Sword swept forward and down, lunging.
    "slash": {"head": (0.60, 0.80), "neck": (0.57, 0.69), "hip": (0.50, 0.40),
              "l_elbow": (0.42, 0.56), "l_hand": (0.36, 0.48),
              "r_elbow": (0.72, 0.64), "r_hand": (0.86, 0.60),
              "l_knee": (0.40, 0.20), "l_foot": (0.28, 0.0),
              "r_knee": (0.68, 0.22), "r_foot": (0.76, 0.0)},
    # Struck: head snapped back, arms flung up.
    "hit_react": {"head": (0.34, 0.80), "neck": (0.41, 0.69), "hip": (0.52, 0.42),
                  "l_elbow": (0.36, 0.80), "l_hand": (0.30, 0.94),
                  "r_elbow": (0.60, 0.80), "r_hand": (0.70, 0.92),
                  "l_knee": (0.46, 0.21), "l_foot": (0.38, 0.0),
                  "r_knee": (0.64, 0.22), "r_foot": (0.70, 0.0)},
}


def swap_sides(pose: PoseDict) -> PoseDict:
    """Rename left<->right joints without moving them: the other half of a stride."""
    out: PoseDict = {}
    for joint, xy in pose.items():
        if joint.startswith("l_"):
            joint = "r_" + joint[2:]
        elif joint.startswith("r_"):
            joint = "l_" + joint[2:]
        out[joint] = xy
    return out


def side_joint(joint: str, facing: str) -> str:
    """Name of a joint after mirroring: mirror() swaps l_/r_, so a left-facing
    figure's lead hand ("r_hand" when facing right) is stored as "l_hand"."""
    if facing == "left" and joint[:2] in ("l_", "r_"):
        return ("r_" if joint[0] == "l" else "l_") + joint[2:]
    return joint


def pose_named(name: str, facing: str = "right") -> PoseDict:
    """A pose by name. A "~" suffix means the other half of the stride (sides swapped)."""
    swapped = name.endswith("~")
    base = name.rstrip("~")
    pose = dict(MOVE_POSES[base] if base in MOVE_POSES else POSES[base])
    if swapped:
        pose = swap_sides(pose)
    return mirror(pose) if facing == "left" else pose


def rotate(pose: PoseDict, degrees: float) -> PoseDict:
    """Rotate the whole body around the hip (counter-clockwise for + degrees)."""
    if not degrees:
        return pose
    a = math.radians(degrees)
    cos, sin = math.cos(a), math.sin(a)
    cx, cy = pose["hip"]
    return {j: (cx + (x - cx) * cos - (y - cy) * sin, cy + (x - cx) * sin + (y - cy) * cos)
            for j, (x, y) in pose.items()}


@dataclass(frozen=True)
class Key:
    t: float                 # seconds after the move starts
    pose: str                # name in MOVE_POSES or POSES ("~" = sides swapped)
    dx: float = 0.0          # forward travel since the move started, in figure heights
    dy: float = 0.0          # height of the feet's origin above the ground, figure heights
    rot: float = 0.0         # body rotation, degrees; + leans backward
    ease: str = "in_out"     # how pose and rotation reach this key
    ease_y: str | None = None  # how height reaches this key (default: `ease`)
    turned: bool = False     # body faces the other way (e.g. back to the bar)
    trail: bool = False      # draw motion trails while moving into this key
    impact: str | None = None  # a strike lands at this key, with this joint ("sword" = blade tip)


@dataclass(frozen=True)
class Move:
    keys: tuple[Key, ...]
    # Travel moves (walk, run): `keys` are one evenly spaced cycle, repeated
    # until the figure reaches its target x. `cycle_dx` heights per `period` s.
    cycle_dx: float = 0.0
    period: float = 0.0

    @property
    def is_travel(self) -> bool:
        return self.cycle_dx > 0

    @property
    def duration(self) -> float:
        return self.keys[-1].t


MOVES: dict[str, Move] = {
    "walk": Move(cycle_dx=0.9, period=1.0, keys=(
        Key(0.25, "walk_pass"), Key(0.5, "walk~"), Key(0.75, "walk_pass~"), Key(1.0, "walk"),
    )),
    "run": Move(cycle_dx=1.6, period=0.5, keys=(
        Key(0.125, "run_pass"), Key(0.25, "run_contact~"), Key(0.375, "run_pass~"),
        Key(0.5, "run_contact"),
    )),
    "jump": Move(keys=(
        Key(0.12, "crouch"),                                         # anticipation
        Key(0.22, "takeoff", dx=0.10, dy=0.06, ease="out"),
        Key(0.45, "tuck", dx=0.40, dy=0.55, ease_y="out"),           # rising slows
        Key(0.66, "takeoff", dx=0.62, dy=0.05, ease_y="in"),         # falling speeds up
        Key(0.74, "land", dx=0.68),                                  # absorb
        Key(0.98, "stand", dx=0.70, ease="out"),                     # settle
    )),
    "backflip": Move(keys=(
        Key(0.12, "crouch"),
        Key(0.22, "takeoff", dx=-0.05, dy=0.15, rot=25, ease="out"),
        # Stretched while upside down (reads clearly), tucked only for the fast part.
        Key(0.36, "takeoff", dx=-0.20, dy=0.62, rot=150, ease_y="out", trail=True),
        Key(0.50, "tuck", dx=-0.35, dy=0.60, rot=270, ease="linear", trail=True),
        Key(0.62, "takeoff", dx=-0.45, dy=0.15, rot=345, ease_y="in", trail=True),
        Key(0.70, "land", dx=-0.50, rot=360),
        Key(0.95, "stand", dx=-0.50, rot=360, ease="out"),
    )),
    # Fosbury flop, done after a run-up: plant, turn the back to the bar, arch
    # over it head first, flick the legs up, land on the back.
    "flop": Move(keys=(
        Key(0.10, "run_contact", dx=0.30, rot=12),                   # plant, lean back
        Key(0.20, "takeoff", dx=0.45, dy=0.10, ease="out"),
        Key(0.36, "arch", dx=0.72, dy=0.48, rot=45, ease_y="out", turned=True, trail=True),
        Key(0.50, "arch", dx=0.95, dy=0.64, rot=90, ease_y="out", turned=True, trail=True),  # over the bar
        Key(0.64, "pike", dx=1.18, dy=0.42, rot=125, ease_y="in", turned=True, trail=True),  # legs clear
        Key(0.80, "pike", dx=1.38, dy=-0.08, rot=105, ease_y="in", turned=True, trail=True), # hit the mat
        Key(1.05, "lie", dx=1.42, dy=-0.21, rot=90, ease="out", turned=True),    # settle on the back
    )),

    # --- Fighting: wind-up, snappy strike ("back" overshoots), short hold, recover. ---
    "stance": Move(keys=(Key(0.18, "stance", ease="out"),)),
    "punch": Move(keys=(
        Key(0.10, "punch_wind", dx=-0.03),
        Key(0.17, "punch", dx=0.15, ease="back", impact="r_hand", trail=True),
        Key(0.30, "punch", dx=0.15),
        Key(0.50, "stance", dx=0.10),
    )),
    "kick": Move(keys=(
        Key(0.12, "kick_chamber"),
        Key(0.22, "kick", dx=0.06, ease="back", impact="r_foot", trail=True),
        Key(0.38, "kick", dx=0.06),
        Key(0.50, "kick_chamber", dx=0.05),
        Key(0.66, "stance", dx=0.05),
    )),
    "slash": Move(keys=(
        Key(0.14, "slash_wind", dx=-0.03),
        Key(0.24, "slash", dx=0.18, ease="back", impact="sword", trail=True),
        Key(0.40, "slash", dx=0.18),
        Key(0.62, "stance", dx=0.14),
    )),
    "block": Move(keys=(
        Key(0.08, "block", dx=-0.04, ease="out"),
        Key(0.40, "block", dx=-0.06),
        Key(0.58, "stance", dx=-0.06),
    )),
    "dodge": Move(keys=(
        Key(0.10, "dodge", dx=-0.14, ease="out", trail=True),
        Key(0.38, "dodge", dx=-0.16),
        Key(0.60, "stance", dx=-0.14),
    )),
    "hit_react": Move(keys=(
        Key(0.06, "hit_react", dx=-0.10, ease="out", trail=True),
        Key(0.28, "hit_react", dx=-0.14),
        Key(0.55, "stance", dx=-0.15),
    )),
    # Thrown backwards through the air, lands on the back, small bounce.
    "knockback": Move(keys=(
        Key(0.06, "hit_react", dx=-0.12, dy=0.05, rot=15, ease="out", trail=True),
        Key(0.30, "hit_react", dx=-0.40, dy=0.30, rot=55, ease_y="out", trail=True),
        Key(0.55, "lie", dx=-0.62, dy=-0.27, rot=90, ease_y="in", trail=True),
        Key(0.68, "lie", dx=-0.66, dy=-0.20, rot=86, ease="out"),
        Key(0.82, "lie", dx=-0.67, dy=-0.27, rot=90, ease="in"),
    )),
    "get_up": Move(keys=(
        Key(0.25, "land", dy=-0.10, rot=45),
        Key(0.50, "crouch"),
        Key(0.75, "stance", ease="out"),
    )),
}

# Moves a fighter makes when struck (or blocking), and how big the impact looks.
REACTIONS = {"block": 1, "hit_react": 2, "knockback": 3}


@dataclass(frozen=True)
class Step:
    move: str
    at: float | None = None    # start time in seconds (None: right after the previous step)
    to_x: float | None = None  # target x in pixels (travel moves only)


@dataclass(frozen=True)
class _AbsKey:
    t: float
    pose: PoseDict  # already mirrored for the facing at this key
    x: float        # pixels
    y: float        # pixels above the ground
    rot: float      # degrees, counter-clockwise on screen
    ease: str
    ease_y: str
    facing: str
    trail: bool = False


def _opposite(facing: str) -> str:
    return "left" if facing == "right" else "right"


class Track:
    """One character's moves laid out in time. `state(t)` gives pose and position."""

    def __init__(self, x: float, facing: str, height: int, steps: Sequence[Step], pose: str = "stand"):
        self.height = height
        self.keys: list[_AbsKey] = [_AbsKey(0.0, pose_named(pose, facing), x, 0.0, 0.0, "linear", "linear", facing)]
        self.events: list[tuple[float, str]] = []   # (start time, move name) per step
        self.impacts: list[tuple[float, str]] = []  # (time, joint) when a strike lands
        for step in steps:
            self._add(step)
        self._times = [k.t for k in self.keys]

    @property
    def end_time(self) -> float:
        return self.keys[-1].t

    def _add(self, step: Step) -> None:
        move = MOVES[step.move]
        last = self.keys[-1]
        start = last.t if step.at is None else max(step.at, last.t)
        if start > last.t:
            self.keys.append(replace(last, t=start, ease="linear", ease_y="linear"))  # hold
        self.events.append((start, step.move))
        if move.is_travel:
            self._add_travel(move, start, step.to_x if step.to_x is not None else last.x)
        else:
            self._add_fixed(move, start)
        self._normalize_rotation()

    def _add_fixed(self, move: Move, start: float) -> None:
        base = self.keys[-1]
        direction = 1 if base.facing == "right" else -1
        for key in move.keys:
            facing = _opposite(base.facing) if key.turned else base.facing
            # "Backward" is counter-clockwise for a right-facing body, clockwise for left.
            sign = 1 if facing == "right" else -1
            self.keys.append(_AbsKey(
                t=start + key.t, pose=pose_named(key.pose, facing),
                x=base.x + direction * key.dx * self.height, y=key.dy * self.height,
                rot=sign * key.rot, ease=key.ease, ease_y=key.ease_y or key.ease, facing=facing,
                trail=key.trail,
            ))
            if key.impact:
                self.impacts.append((start + key.t, side_joint(key.impact, facing)))

    def _add_travel(self, move: Move, start: float, to_x: float) -> None:
        base = self.keys[-1]
        distance = abs(to_x - base.x)
        if distance < 1:
            return
        facing = "right" if to_x > base.x else "left"
        n = len(move.keys)
        step_dx = move.cycle_dx / n * self.height   # pixels per key
        step_t = move.period / n
        count = max(2, round(distance / step_dx))
        scale = distance / (count * step_dx)        # stretch strides to land exactly on to_x
        direction = 1 if facing == "right" else -1
        for i in range(1, count + 1):
            key = move.keys[(i - 1) % n]
            self.keys.append(_AbsKey(
                t=start + i * step_t * scale, pose=pose_named(key.pose, facing),
                x=base.x + direction * i * step_dx * scale, y=0.0, rot=0.0,
                ease=key.ease, ease_y=key.ease_y or key.ease, facing=facing,
            ))

    def _normalize_rotation(self) -> None:
        # After a full flip (360 degrees) snap back to 0 so the next move doesn't unspin.
        last = self.keys[-1]
        wrapped = (last.rot + 180) % 360 - 180
        if abs(wrapped - last.rot) > 1e-6:
            self.keys.append(replace(last, t=last.t + 1e-4, rot=wrapped, ease="linear", ease_y="linear"))

    def state(self, t: float) -> tuple[PoseDict, float, float]:
        """(rotated unit pose, x px, height px above the ground) at time t."""
        i = bisect_right(self._times, t)
        if i == 0:
            a = b = self.keys[0]
        elif i >= len(self.keys):
            a = b = self.keys[-1]
        else:
            a, b = self.keys[i - 1], self.keys[i]
        p = 1.0 if b.t <= a.t else (t - a.t) / (b.t - a.t)
        pe, py = EASES[b.ease](p), EASES[b.ease_y](p)
        pose = lerp_pose(a.pose, b.pose, pe)
        return rotate(pose, lerp(a.rot, b.rot, pe)), lerp(a.x, b.x, p), lerp(a.y, b.y, py)

    def holding(self, t: float) -> bool:
        """True while standing still between moves (or after the last one)."""
        i = bisect_right(self._times, t)
        if i == 0 or i >= len(self.keys):
            return True
        a, b = self.keys[i - 1], self.keys[i]
        return a.pose is b.pose and a.x == b.x and a.y == b.y and a.rot == b.rot

    def reaction_at(self, t: float, window: float = 0.15) -> str | None:
        """The reaction move (block, hit_react, ...) this fighter starts around time t."""
        for start, move in self.events:
            if move in REACTIONS and t - window <= start <= t + 0.05:
                return move
        return None

    def trailing(self, t: float) -> bool:
        """True while moving into a key marked `trail` (fast flips, swings, hits)."""
        i = bisect_right(self._times, t)
        return 0 < i < len(self.keys) and self.keys[i].trail

    def facing_at(self, t: float) -> str:
        i = max(0, bisect_right(self._times, t) - 1)
        return self.keys[i].facing


def _main() -> None:
    from shorts.render.action import write_demo

    parser = argparse.ArgumentParser(description="Move library tools")
    parser.add_argument("--demo", choices=["fosbury", "fight", "jump", "backflip"], help="render a demo to output/debug/")
    args = parser.parse_args()
    if args.demo:
        for path in write_demo(args.demo):
            print(f"wrote {path}")


if __name__ == "__main__":
    _main()
