"""Draws one stick figure from a unit pose."""

from functools import lru_cache

from PIL import Image, ImageDraw

from shorts.render.poses import PoseDict

# Bones drawn as lines, in order. "shoulder" is derived, not stored in poses.
_BONES = [
    ("hip", "l_knee"), ("l_knee", "l_foot"),
    ("hip", "r_knee"), ("r_knee", "r_foot"),
    ("neck", "hip"),
    ("shoulder", "l_elbow"), ("l_elbow", "l_hand"),
    ("shoulder", "r_elbow"), ("r_elbow", "r_hand"),
]

# Arms attach this far down the spine, so raised arms clear the head.
_SHOULDER_DROP = 0.15


def render_figure(
    pose: PoseDict,
    height: int,
    style: dict,
    ink: tuple[int, int, int],
    head_color: tuple[int, int, int] | None = None,
) -> tuple[Image.Image, tuple[int, int]]:
    """Render a figure on a transparent layer.

    Returns (layer, foot_point): paste the layer so that foot_point lands on the
    spot where the figure's feet should touch the ground. foot_point is the unit
    origin (0.5, 0); for a rotated or airborne pose it may lie outside the layer.
    """
    key = (tuple(sorted(pose.items())), height, ink, head_color)
    return _render_cached(key, style["figure"]["line_width"], style["figure"]["head_ratio"],
                          style["figure"]["supersample"])


@lru_cache(maxsize=256)
def _render_cached(key, line_width: int, head_ratio: float, ss: int):
    pose_items, height, ink, head_color = key
    pose = dict(pose_items)
    (nx, ny), (hx_, hy_) = pose["neck"], pose["hip"]
    pose["shoulder"] = (nx + (hx_ - nx) * _SHOULDER_DROP, ny + (hy_ - ny) * _SHOULDER_DROP)

    # Draw at `ss` times the size, then shrink: Pillow lines aren't anti-aliased,
    # so supersampling is what makes the edges smooth.
    h = height * ss
    lw = line_width * ss
    # Size the layer to the pose itself (a flipping figure can be upside down).
    hx0, hy0 = pose["head"]
    xs = [x for x, _ in pose.values()] + [hx0 - head_ratio, hx0 + head_ratio]
    ys = [y for _, y in pose.values()] + [hy0 - head_ratio, hy0 + head_ratio]
    w_px = int((max(xs) - min(xs)) * h) + 2 * lw
    h_px = int((max(ys) - min(ys)) * h) + 2 * lw
    # Pixel position of the unit origin (0.5, 0) inside the layer.
    foot_x = lw + (0.5 - min(xs)) * h
    foot_y = lw + max(ys) * h

    def to_px(joint: str) -> tuple[float, float]:
        # The one place unit coordinates (y up) become Pillow pixels (y down).
        x, y = pose[joint]
        return (foot_x + (x - 0.5) * h, foot_y - y * h)

    layer = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cap = lw / 2

    for a, b in _BONES:
        if a not in pose or b not in pose:
            continue
        pa, pb = to_px(a), to_px(b)
        draw.line([pa, pb], fill=ink, width=lw)
        # Pillow has no round line caps; a dot on each end fakes them.
        for px, py in (pa, pb):
            draw.ellipse([px - cap, py - cap, px + cap, py + cap], fill=ink)

    hx, hy = to_px("head")
    r = head_ratio * h
    draw.ellipse([hx - r, hy - r, hx + r, hy + r], outline=head_color or ink, width=lw)

    small = layer.resize((w_px // ss, h_px // ss), Image.LANCZOS)
    return small, (int(foot_x / ss), int(foot_y / ss))


def head_top_y(pose: PoseDict, ground_px: int, height: int, head_ratio: float) -> int:
    """Pixel y of the top of the head (for placing speech bubbles)."""
    return int(ground_px - (pose["head"][1] + head_ratio) * height)


def x_extent(pose: PoseDict, height: int, line_width: int, head_ratio: float) -> tuple[float, float]:
    """Leftmost/rightmost drawn pixel offsets relative to the figure's center line."""
    xs = [x for x, _ in pose.values()]
    head_x = pose["head"][0]
    lo = min(min(xs), head_x - head_ratio)
    hi = max(max(xs), head_x + head_ratio)
    pad = line_width / 2
    return ((lo - 0.5) * height - pad, (hi - 0.5) * height + pad)
