"""Props: simple line drawings of the topic's objects (shark, tree, clock, ...).

Each prop is one function that draws in a unit box: x 0-1, y 0-1 with y UP and
the origin at the bottom (same convention as poses). `Pen` converts to pixels.

To add a prop: add its name to PROP_KINDS in models.py, write a `_draw_<kind>`
function here and register it in PROP_DRAWERS.
"""

import math
from collections.abc import Callable
from functools import lru_cache

from PIL import Image, ImageDraw

from shorts.render.captions import load_font

RGB = tuple[int, int, int]


class Pen:
    """Draws unit-box shapes onto a square pixel layer."""

    def __init__(self, draw: ImageDraw.ImageDraw, size: int, margin: int, lw: int, ink: RGB, accent: RGB):
        self.draw, self.size, self.margin, self.lw = draw, size, margin, lw
        self.ink, self.accent = ink, accent

    def px(self, x: float, y: float) -> tuple[float, float]:
        # The one place unit coords (y up) become Pillow pixels (y down).
        return (self.margin + x * self.size, self.margin + (1 - y) * self.size)

    def line(self, *points: tuple[float, float]) -> None:
        pts = [self.px(x, y) for x, y in points]
        self.draw.line(pts, fill=self.ink, width=self.lw, joint="curve")
        r = self.lw / 2
        for px, py in (pts[0], pts[-1]):  # round caps
            self.draw.ellipse([px - r, py - r, px + r, py + r], fill=self.ink)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, fill: RGB | None = None) -> None:
        x0, y0 = self.px(cx - rx, cy + ry)
        x1, y1 = self.px(cx + rx, cy - ry)
        self.draw.ellipse([x0, y0, x1, y1], outline=self.ink, width=self.lw, fill=fill)

    def arc(self, cx: float, cy: float, r: float, start: float, end: float) -> None:
        """Arc in degrees, Pillow convention (0 = 3 o'clock, clockwise)."""
        x0, y0 = self.px(cx - r, cy + r)
        x1, y1 = self.px(cx + r, cy - r)
        self.draw.arc([x0, y0, x1, y1], start, end, fill=self.ink, width=self.lw)

    def polygon(self, *points: tuple[float, float], fill: RGB | None = None) -> None:
        self.draw.polygon([self.px(x, y) for x, y in points], outline=self.ink, fill=fill, width=self.lw)


def _draw_shark(p: Pen) -> None:
    # Torpedo body, pointed nose on the right, as one closed outline.
    p.line((0.96, 0.44), (0.80, 0.55), (0.55, 0.60), (0.32, 0.56), (0.16, 0.46),
           (0.30, 0.37), (0.55, 0.33), (0.80, 0.35), (0.96, 0.44))
    p.line((0.62, 0.595), (0.45, 0.82), (0.42, 0.59))                # dorsal fin, swept back
    p.line((0.16, 0.46), (0.03, 0.70), (0.09, 0.46), (0.05, 0.28), (0.16, 0.46))  # tail
    p.line((0.58, 0.335), (0.48, 0.18), (0.66, 0.34))                # side fin
    p.line((0.70, 0.40), (0.68, 0.50))                               # gills
    p.line((0.65, 0.40), (0.63, 0.50))
    p.line((0.80, 0.38), (0.90, 0.40))                               # mouth
    p.ellipse(0.84, 0.48, 0.015, 0.015, fill=p.ink)                  # eye


def _draw_tree(p: Pen) -> None:
    # Pine silhouette as one closed zig-zag outline (no overlapping lines).
    p.line((0.50, 0.98), (0.66, 0.70), (0.58, 0.70), (0.76, 0.44), (0.65, 0.44),
           (0.84, 0.18), (0.16, 0.18), (0.35, 0.44), (0.24, 0.44), (0.42, 0.70),
           (0.34, 0.70), (0.50, 0.98))
    p.line((0.45, 0.0), (0.45, 0.18))                                # trunk
    p.line((0.55, 0.0), (0.55, 0.18))


def _squiggle(p: Pen, x0: float, x1: float, y: float, amp: float, waves: float) -> None:
    n = 24
    p.line(*[(x0 + (x1 - x0) * k / n, y + amp * math.sin(waves * 2 * math.pi * k / n)) for k in range(n + 1)])


def _draw_brain(p: Pen) -> None:
    # Bumpy outline: an ellipse whose radius ripples, like the brain's folds.
    n = 120
    outline = []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        ripple = 1 + 0.05 * math.cos(11 * a)
        outline.append((0.5 + 0.44 * ripple * math.cos(a), 0.52 + 0.32 * ripple * math.sin(a)))
    p.line(*outline)
    p.line(*[(0.5 + 0.03 * math.sin(k * 1.3), 0.80 - 0.56 * k / 12) for k in range(13)])  # center fold
    _squiggle(p, 0.16, 0.42, 0.62, 0.03, 1.5)
    _squiggle(p, 0.20, 0.42, 0.40, 0.03, 1.5)
    _squiggle(p, 0.58, 0.84, 0.62, 0.03, 1.5)
    _squiggle(p, 0.58, 0.80, 0.40, 0.03, 1.5)


def _draw_clock(p: Pen) -> None:
    p.ellipse(0.5, 0.5, 0.45, 0.45)
    for k in range(12):
        a = k * math.pi / 6
        r0 = 0.36 if k % 3 else 0.32  # longer ticks at 12, 3, 6, 9
        p.line((0.5 + r0 * math.sin(a), 0.5 + r0 * math.cos(a)),
               (0.5 + 0.40 * math.sin(a), 0.5 + 0.40 * math.cos(a)))
    p.line((0.5, 0.5), (0.5, 0.80))                                  # minute hand
    p.line((0.5, 0.5), (0.70, 0.5))                                  # hour hand
    p.ellipse(0.5, 0.5, 0.02, 0.02, fill=p.ink)


def _draw_question(p: Pen) -> None:
    p.arc(0.5, 0.68, 0.22, 160, 380)                                 # hook top
    end = math.radians(20)  # arc ends 20 degrees below 3 o'clock
    p.line((0.5 + 0.22 * math.cos(end), 0.68 - 0.22 * math.sin(end)),
           (0.5, 0.42), (0.5, 0.28))                                 # neck
    p.ellipse(0.5, 0.10, 0.035, 0.035, fill=p.ink)                   # dot


def _draw_arrow(p: Pen) -> None:
    p.line((0.08, 0.5), (0.90, 0.5))
    p.line((0.66, 0.72), (0.90, 0.5), (0.66, 0.28))


def _draw_star(p: Pen) -> None:
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        r = 0.46 if k % 2 == 0 else 0.19
        pts.append((0.5 + r * math.cos(a), 0.48 + r * math.sin(a)))
    p.polygon(*pts, fill=p.accent)  # the star is the one prop that uses the accent


def _draw_bar(p: Pen) -> None:
    # High-jump bar, seen from the side: two close posts and a short crossbar.
    p.line((0.40, 0.0), (0.40, 1.0))
    p.line((0.60, 0.0), (0.60, 1.0))
    p.line((0.32, 0.95), (0.68, 0.95))


def _draw_mat(p: Pen) -> None:
    # Landing mat: a low, wide block.
    p.line((0.0, 0.0), (0.0, 0.14), (1.0, 0.14), (1.0, 0.0))
    p.line((0.04, 0.07), (0.96, 0.07))


PROP_DRAWERS: dict[str, Callable[[Pen], None]] = {
    "shark": _draw_shark,
    "tree": _draw_tree,
    "brain": _draw_brain,
    "clock": _draw_clock,
    "question": _draw_question,
    "arrow": _draw_arrow,
    "star": _draw_star,
    "bar": _draw_bar,
    "mat": _draw_mat,
}


def prop_size_px(size: str, style: dict) -> int:
    return int(style["figure"]["height_px"] * style["props"]["size_ratio"][size])


@lru_cache(maxsize=128)
def _render_prop_cached(kind: str, size: int, lw: int, ss: int, ink: RGB, accent: RGB) -> Image.Image:
    # Supersample like figures: draw big, shrink, for smooth edges.
    s, line = size * ss, lw * ss
    margin = line
    layer = Image.new("RGBA", (s + 2 * margin, s + 2 * margin), (0, 0, 0, 0))
    PROP_DRAWERS[kind](Pen(ImageDraw.Draw(layer), s, margin, line, ink, accent))
    return layer.resize((layer.width // ss, layer.height // ss), Image.LANCZOS)


def render_prop(kind: str, size: int, style: dict, ink: RGB, accent: RGB) -> Image.Image:
    """Transparent square layer with the prop; its bottom edge is the prop's floor."""
    fig = style["figure"]
    return _render_prop_cached(kind, size, fig["line_width"], fig["supersample"], ink, accent)


def scaled(layer: Image.Image, scale: float) -> Image.Image | None:
    """Layer resized for a pop animation (None when invisible)."""
    scale = round(scale, 2)  # quantize so resized layers repeat and stay cheap
    if scale <= 0.01:
        return None
    if scale == 1:
        return layer
    w, h = max(1, int(layer.width * scale)), max(1, int(layer.height * scale))
    return layer.resize((w, h), Image.LANCZOS)


def render_label(text: str, size_px: int, style: dict, ink: RGB) -> Image.Image:
    """A one-line text label (for versus sides and timeline points)."""
    font = load_font(style["bubble"]["font"], size_px)
    left, top, right, bottom = font.getbbox(text)
    layer = Image.new("RGBA", (right - left + 4, bottom - top + 4), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((2 - left, 2 - top), text, font=font, fill=ink)
    return layer
