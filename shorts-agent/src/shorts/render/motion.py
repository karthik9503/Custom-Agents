"""Easing and interpolation helpers for in-scene actions. Pure math, no drawing."""

import math

from shorts.render.poses import PoseDict


def progress(t: float, start: float, duration: float) -> float:
    """0 before `start`, 1 after `start + duration`, linear in between."""
    if duration <= 0:
        return 1.0 if t >= start else 0.0
    return min(1.0, max(0.0, (t - start) / duration))


def ease_out(p: float) -> float:
    return 1 - (1 - p) ** 3


def ease_in_out(p: float) -> float:
    return 0.5 - math.cos(math.pi * p) / 2


def ease_out_back(p: float) -> float:
    """Overshoots ~10% then settles at 1: the "pop"."""
    c1 = 1.70158
    return 1 + (c1 + 1) * (p - 1) ** 3 + c1 * (p - 1) ** 2


def lerp(a: float, b: float, p: float) -> float:
    return a + (b - a) * p


def lerp_pose(a: PoseDict, b: PoseDict, p: float) -> PoseDict:
    """Blend two poses joint by joint."""
    return {j: (lerp(a[j][0], b[j][0], p), lerp(a[j][1], b[j][1], p)) for j in a}
