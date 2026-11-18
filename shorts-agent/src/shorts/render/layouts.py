"""One render function per scene layout, picked from LAYOUT_RENDERERS.

Each function has the same signature: (renderer, frame image, time in seconds).
It draws the layout's figures/props/numbers onto the frame; SceneRenderer has
already filled the background and adds the caption afterwards.

To add a layout: add its name to LAYOUTS (and LAYOUT_LIMITS) in models.py, write
a `draw_<layout>` function here, register it below, and describe it in the
scene-director and video-style skills.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from shorts.render.action import action_height, draw_ground
from shorts.render.captions import load_font
from shorts.render.choreo import action_scene
from shorts.render.figure import x_extent
from shorts.render.motion import ease_out, progress
from shorts.render.poses import POSES, get_pose
from shorts.render.props import prop_size_px, render_label, render_prop, scaled

if TYPE_CHECKING:
    from shorts.render.scene import SceneRenderer


# --- shared bits -------------------------------------------------------------

def _prop_layer(r: SceneRenderer, k: int, max_size: float | None = None) -> Image.Image:
    prop = r.scene["props"][k]
    size = prop_size_px(prop["size"], r.style)
    if max_size is not None:
        size = min(size, int(max_size))
    return r.memo(("prop", k, size), lambda: render_prop(prop["kind"], size, r.style, r.ink, r.accent))


def _fit_label(r: SceneRenderer, text: str, size_px: int, max_w: float) -> Image.Image:
    """Label layer, shrunk until it fits `max_w` (never below the bubble font size)."""
    def build() -> Image.Image:
        size = size_px
        layer = render_label(text, size, r.style, r.ink)
        while layer.width > max_w and size > r.style["bubble"]["size_px"]:
            size = max(r.style["bubble"]["size_px"], int(size * 0.9))
            layer = render_label(text, size, r.style, r.ink)
        return layer
    return r.memo(("label", text, size_px), build)


def _line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], ink, lw: int) -> None:
    """Thick line with round caps, matching the figures' pen."""
    draw.line(points, fill=ink, width=lw, joint="curve")
    for x, y in (points[0], points[-1]):
        draw.ellipse([x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2], fill=ink)


def _clamped_x(r: SceneRenderer, c: dict, height: int) -> float:
    """Character center x, nudged so the whole figure stays in the safe zone."""
    fig = r.style["figure"]
    # Use the widest of the start and end pose, so a pose_change can't leave the zone.
    names = [c["pose"]] + ([c["end_pose"]] if c.get("end_pose") else [])
    extents = [x_extent(get_pose(n, c["facing"]), height, fig["line_width"], fig["head_ratio"]) for n in names]
    lo, hi = min(e[0] for e in extents), max(e[1] for e in extents)
    return min(max(c["x"] * r.width, r.left - lo), r.right - hi)


def _pose_reach(r: SceneRenderer, c: dict) -> float:
    """Tallest point of the character's poses, in figure heights (head top or hands)."""
    head_r = r.style["figure"]["head_ratio"]
    names = [c["pose"], "walk"] + ([c["end_pose"]] if c.get("end_pose") else [])
    return max(max(max(y for _, y in POSES[n].values()), POSES[n]["head"][1] + head_r) for n in names)


def format_number(value: float, target: float) -> str:
    """Format like the target: 450 -> "450", 1500000 -> "1,500,000", 3.5 -> "3.5"."""
    decimals = 0 if float(target).is_integer() else min(2, len(repr(float(target)).split(".")[1]))
    return f"{value:,.{decimals}f}"


# --- layouts -----------------------------------------------------------------

def draw_dialogue(r: SceneRenderer, img: Image.Image, t: float) -> None:
    """Figures (and props) side by side on the ground line; the classic layout."""
    fig = r.style["figure"]
    height = fig["height_px"]
    ground = int(r.height * fig["ground_y"])

    for k, prop in enumerate(r.scene["props"]):
        layer = _prop_layer(r, k)
        # Keep the drawn pixels (not the whole square layer) inside the safe zone.
        x0, _, x1, _ = layer.getbbox()
        lo, hi = x0 - layer.width / 2, x1 - layer.width / 2
        cx = min(max(prop["x"] * r.width, r.left - lo), r.right - hi)
        scale = r.prop_scale(k, t)
        # The layer has a one-pen margin under the drawing; sink it so props stand on the ground.
        r.paste_bottom(img, scaled(layer, scale), cx, ground + r.gap * scale)

    placements = []
    for k, c in enumerate(r.scene["characters"]):
        cx = r.memo(("cx", k), lambda c=c: _clamped_x(r, c, height))
        r.draw_figure(img, c, k, cx, ground, height, t)
        placements.append((c, cx, ground, height))
    r.draw_bubbles(img, placements, t)


def draw_closeup(r: SceneRenderer, img: Image.Image, t: float) -> None:
    """One figure, scaled up to fill the space between the caption and the bottom."""
    c = r.scene["characters"][0]
    ground = r.bottom - r.gap
    top = r.caption_bottom + 2 * r.gap
    if c.get("says"):  # leave room for the bubble above the head
        top += r.bubble_height(c["says"]) + r.gap
    height = int((ground - top) / _pose_reach(r, c))
    r.draw_figure(img, c, 0, r.center_x, ground, height, t)
    r.draw_bubbles(img, [(c, r.center_x, ground, height)], t)


def draw_big_number(r: SceneRenderer, img: Image.Image, t: float) -> None:
    """A big centered number (optionally counting up), a unit under it, a small figure."""
    cfg = r.style["layouts"]["big_number"]
    number = r.scene["number"]
    final_text = format_number(number, number)

    def fit_font():
        size = cfg["size_px"]
        font = load_font(r.style["caption"]["font"], size)
        while font.getlength(final_text) > r.safe_w and size > r.style["caption"]["size_px"]:
            size = int(size * 0.9)
            font = load_font(r.style["caption"]["font"], size)
        return font
    font = r.memo("number_font", fit_font)

    p = 1.0
    if r.action() == "count_up":
        p = ease_out(progress(t, 0, r.style["actions"]["count_up_share"] * r.duration))
    cy = r.height * cfg["y"]
    ImageDraw.Draw(img).text((r.center_x, cy), format_number(number * p, number),
                             font=font, fill=r.ink, anchor="mm")

    text_bottom = cy + font.size / 2
    if r.scene.get("unit"):
        label = _fit_label(r, r.scene["unit"], cfg["unit_size_px"], r.safe_w)
        r.paste_center(img, label, r.center_x, text_bottom + r.gap + label.height / 2)
        text_bottom += r.gap + label.height

    fig = r.style["figure"]
    height = int(fig["height_px"] * cfg["figure_scale"])
    for k, c in enumerate(r.scene["characters"]):
        # Small, off to the left side, so the number stays the star. A wide unit
        # spans the left side too, so stand low enough that raised hands clear it.
        cx = r.left + height * 0.5
        clear = text_bottom + r.gap + _pose_reach(r, c) * height
        ground = min(max(r.height * fig["ground_y"], clear), r.bottom - r.gap)
        r.draw_figure(img, c, k, cx, int(ground), height, t)


def draw_versus(r: SceneRenderer, img: Image.Image, t: float) -> None:
    """Split screen: a prop and a label on each side, a "VS" badge on the divider."""
    cfg = r.style["layouts"]["versus"]
    draw = ImageDraw.Draw(img)
    cy = r.height * cfg["y"]
    badge_r = cfg["badge_radius_px"]
    half = r.safe_w / 2

    _line(draw, [(r.center_x, r.caption_bottom + 3 * r.gap), (r.center_x, r.bottom - 3 * r.gap)],
          r.ink, r.gap // 2)

    # Each prop is centered in the free space between the badge and the safe edge.
    side_w = half - badge_r - r.gap
    max_size = side_w - 2 * r.gap  # leave room for the layer's pen margin
    for k in range(2):
        cx = r.left + side_w / 2 if k == 0 else r.right - side_w / 2
        scale = r.prop_scale(k, t)
        layer = _prop_layer(r, k, max_size)
        r.paste_center(img, scaled(layer, scale), cx, cy)
        if scale > 0:
            label = _fit_label(r, r.scene["props"][k]["label"], cfg["label_size_px"], half - 2 * r.gap)
            r.paste_center(img, label, cx, cy + layer.height / 2 + r.gap + label.height / 2)

    draw.ellipse([r.center_x - badge_r, cy - badge_r, r.center_x + badge_r, cy + badge_r],
                 fill=r.bg, outline=r.ink, width=r.gap // 2)
    vs = _fit_label(r, "VS", cfg["label_size_px"], badge_r * 1.5)
    r.paste_center(img, vs, r.center_x, cy)


def draw_timeline(r: SceneRenderer, img: Image.Image, t: float) -> None:
    """A time arrow with props appearing in order above it, labels below."""
    cfg = r.style["layouts"]["timeline"]
    draw = ImageDraw.Draw(img)
    lw, tick = r.gap, cfg["tick_px"]
    y = r.height * cfg["y"]
    x0, x1 = r.left + lw, r.right - lw

    _line(draw, [(x0, y), (x1, y)], r.ink, lw)
    _line(draw, [(x1 - 2.5 * lw, y - 2 * lw), (x1, y), (x1 - 2.5 * lw, y + 2 * lw)], r.ink, lw)

    props = r.scene["props"]
    slot = (x1 - x0) / len(props)
    stagger = r.style["actions"]["timeline_share"] * r.duration / len(props)
    for k, prop in enumerate(props):
        cx = x0 + slot * (k + 0.5)
        _line(draw, [(cx, y - tick / 2), (cx, y + tick / 2)], r.ink, lw)
        scale = r.prop_scale(k, t, stagger=stagger)
        layer = _prop_layer(r, k, slot * 0.8)
        r.paste_bottom(img, scaled(layer, scale), cx, y - tick / 2 - r.gap + r.gap * scale)
        if scale > 0 and prop.get("label"):
            label = _fit_label(r, prop["label"], cfg["label_size_px"], slot - r.gap)
            r.paste_center(img, label, cx, y + tick / 2 + r.gap + label.height / 2)


def draw_action(r: SceneRenderer, img: Image.Image, t: float) -> None:
    """Full-body choreography on a ground line: runs, flips, fights (render/moves.py)."""
    scene = r.memo("action", lambda: action_scene(r.scene, r.style, r.ink, r.accent, r.bg))
    height = action_height(r.style)
    draw_ground(img, scene.ground, r.style, r.ink)
    for k, prop in enumerate(r.scene["props"]):
        size = int(height * r.style["props"]["size_ratio"][prop["size"]])
        layer = r.memo(("action_prop", k), lambda prop=prop, size=size:
                       render_prop(prop["kind"], size, r.style, r.ink, r.accent))
        r.paste_bottom(img, layer, prop["x"] * r.width, scene.ground + r.gap)
    out = scene.draw(img, round(t * r.fps))
    if out is not img:  # screen shake returned a shifted copy
        img.paste(out)


LayoutFn = Callable[["SceneRenderer", Image.Image, float], None]

LAYOUT_RENDERERS: dict[str, LayoutFn] = {
    "dialogue": draw_dialogue,
    "closeup": draw_closeup,
    "big_number": draw_big_number,
    "versus": draw_versus,
    "timeline": draw_timeline,
    "action": draw_action,
}
