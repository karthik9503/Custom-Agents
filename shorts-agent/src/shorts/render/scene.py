"""Renders one scene frame by frame.

SceneRenderer owns what every layout shares: background, caption, timing, and the
figure/prop animation helpers. The layout-specific drawing lives in layouts.py,
one function per layout, picked from LAYOUT_RENDERERS.
"""

import math
from collections.abc import Callable

import numpy as np
from PIL import Image, ImageDraw

from shorts.render import layouts
from shorts.render.bubbles import render_bubble
from shorts.render.captions import pop_in_frames, render_caption
from shorts.render.figure import head_top_y, render_figure
from shorts.render.motion import ease_in_out, ease_out, ease_out_back, lerp, lerp_pose, progress
from shorts.render.poses import PoseDict, get_pose, lifted
from shorts.style import hex_to_rgb


def safe_box(style: dict) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) of the safe zone in pixels."""
    w, h = style["canvas"]["width"], style["canvas"]["height"]
    sz = style["safe_zone"]
    return (w * sz["left"], h * sz["top"], w * (1 - sz["right"]), h * (1 - sz["bottom"]))


def draw_safe_zone(img: Image.Image, style: dict) -> None:
    """Debug only: thin outline of the safe zone."""
    color = hex_to_rgb(style["debug"]["safe_zone_color"])
    ImageDraw.Draw(img).rectangle(safe_box(style), outline=color, width=2)


class SceneRenderer:
    """Precomputes everything static about a scene; `frame(i)` adds the motion."""

    def __init__(self, scene: dict, duration: float, style: dict):
        self.scene, self.style, self.duration = scene, style, duration
        canvas, colors = style["canvas"], style["colors"]
        self.fps = canvas["fps"]
        self.width, self.height = canvas["width"], canvas["height"]
        self.n_frames = max(1, round(duration * self.fps))

        self.bg = hex_to_rgb(colors["backgrounds"][scene["background"]])
        # Ink must stay readable on the dark background.
        self.ink = hex_to_rgb(colors["ink_on_night"] if scene["background"] == "night" else colors["ink"])
        self.accent = hex_to_rgb(colors["accent"])
        self.base = Image.new("RGB", (self.width, self.height), self.bg)

        self.left, self.top, self.right, self.bottom = safe_box(style)
        self.safe_w = self.right - self.left
        self.center_x = (self.left + self.right) / 2
        self.gap = style["figure"]["line_width"]  # standard spacing between elements

        # Caption: centered in the safe zone at caption.y, same for every layout.
        # Silent action scenes may have none.
        self.caption_center = (self.center_x, self.height * style["caption"]["y"])
        if scene.get("caption"):
            cap = render_caption(scene["caption"], style, self.safe_w, self.ink, self.accent)
            self.caption_full: Image.Image | None = cap
            self.caption_pop = pop_in_frames(cap, style["caption"]["pop_in_frames"])
            self.caption_bottom = self.caption_center[1] + cap.height / 2
        else:
            self.caption_full, self.caption_pop = None, []
            self.caption_bottom = self.top

        self.draw_layout: Callable[[SceneRenderer, Image.Image, float], None] = (
            layouts.LAYOUT_RENDERERS[scene["layout"]]
        )
        self._memo: dict = {}

    # --- frame loop -------------------------------------------------------

    def frame(self, i: int) -> Image.Image:
        t = i / self.fps
        img = self.base.copy()
        self.draw_layout(self, img, t)
        cap = self.caption_pop[i] if i < len(self.caption_pop) else self.caption_full
        self.paste_center(img, cap, *self.caption_center)  # no-op when there's no caption
        return img

    def frame_at(self, t: float) -> np.ndarray:
        """MoviePy frame function: time in seconds -> HxWx3 uint8 array."""
        i = min(int(round(t * self.fps)), self.n_frames - 1)
        return np.asarray(self.frame(i))

    # --- helpers for layouts ---------------------------------------------

    def memo(self, key, build: Callable):
        """Compute a static layer once per scene and reuse it every frame."""
        if key not in self._memo:
            self._memo[key] = build()
        return self._memo[key]

    def action(self) -> str:
        return self.scene.get("action", "none")

    def paste_center(self, img: Image.Image, layer: Image.Image | None, cx: float, cy: float) -> None:
        if layer is not None:
            img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)

    def paste_bottom(self, img: Image.Image, layer: Image.Image | None, cx: float, bottom: float) -> None:
        if layer is not None:
            img.paste(layer, (int(cx - layer.width / 2), int(bottom - layer.height)), layer)

    # Figures

    def entering(self, t: float) -> float:
        """0 -> 1 progress of the enter_left slide (1 if the action isn't enter_left)."""
        if self.action() != "enter_left":
            return 1.0
        return progress(t, 0, self.style["actions"]["enter_s"])

    def figure_pose(self, c: dict, t: float) -> PoseDict:
        if self.entering(t) < 1:
            return get_pose("walk", "right")  # walking in, facing the way they move
        pose = get_pose(c["pose"], c["facing"])
        if self.action() == "pose_change" and c.get("end_pose"):
            a = self.style["actions"]
            p = progress(t, a["pose_change_at"] * self.duration, a["pose_change_s"])
            pose = lerp_pose(pose, get_pose(c["end_pose"], c["facing"]), ease_in_out(p))
        return pose

    def draw_figure(self, img: Image.Image, c: dict, index: int, cx: float, ground: float,
                    height: int, t: float) -> None:
        fig = self.style["figure"]
        p = self.entering(t)
        if p < 1:  # slide in from just off the left edge
            cx = lerp(-height * 0.5, cx, ease_out(p))
        # Idle bob: sine between rest pose and torso raised by idle_lift; phases
        # spread so figures don't bob in lockstep.
        phase = index / max(1, len(self.scene["characters"]))
        wave = (math.sin(2 * math.pi * (t / fig["idle_period_s"] + phase)) + 1) / 2
        # Round to whole pixels so figure layers can be cached and reused.
        lift_px = round(wave * fig["idle_lift"] * height)
        pose = lifted(self.figure_pose(c, t), lift_px / height)
        # Highlight only the speaker's head, and sparingly: nobody else.
        head = self.accent if c.get("says") else None
        layer, foot = render_figure(pose, height, self.style, self.ink, head)
        img.paste(layer, (int(cx - foot[0]), int(ground - foot[1])), layer)

    def bubble(self, c: dict, cx: float, ground: float, height: int):
        """Static speech-bubble layer + position for speaker `c` (computed once)."""
        return self.memo(("bubble", c["id"]), lambda: self._place_bubble(c, cx, ground, height))

    def bubble_height(self, text: str) -> int:
        style = self.style
        fill = hex_to_rgb(style["colors"]["backgrounds"]["white"])
        layer, _ = render_bubble(text, style, self.safe_w * style["bubble"]["max_width_ratio"], fill, self.ink)
        return layer.height

    def _place_bubble(self, c: dict, cx: float, ground: float, height: int):
        style = self.style
        fill = hex_to_rgb(style["colors"]["backgrounds"]["white"])
        ink = hex_to_rgb(style["colors"]["ink"])  # bubble is always light, so dark text
        max_w = self.safe_w * style["bubble"]["max_width_ratio"]
        pose = get_pose(c["pose"], c["facing"])
        layer, _ = render_bubble(c["says"], style, max_w, fill, ink)
        x = min(max(cx - layer.width / 2, self.left), self.right - layer.width)
        # If the bubble was pushed sideways, redraw it with the tail aimed at the head.
        head_x = cx + (pose["head"][0] - 0.5) * height
        offset = head_x - (x + layer.width / 2)
        if abs(offset) > 1:
            layer, _ = render_bubble(c["says"], style, max_w, fill, ink, tail_offset=offset)
        head_top = head_top_y(pose, int(ground), height, style["figure"]["head_ratio"])
        y = head_top - self.gap - layer.height
        # Never cover the caption; squeeze toward the head instead.
        y = max(y, self.caption_bottom + self.gap)
        return layer, (int(x), int(y))

    def draw_bubbles(self, img: Image.Image, placements: list[tuple[dict, float, float, int]], t: float) -> None:
        """Draw the speaker's bubble once everyone has walked in."""
        if self.entering(t) < 1:
            return
        for c, cx, ground, height in placements:
            if c.get("says"):
                layer, pos = self.bubble(c, cx, ground, height)
                img.paste(layer, pos, layer)

    # Props

    def prop_scale(self, index: int, t: float, stagger: float | None = None) -> float:
        """Pop-in scale for the index-th prop.

        Without `stagger`, props only pop when the scene's action is "pop".
        With it (timeline), props always pop in, `stagger` seconds apart.
        """
        a = self.style["actions"]
        if stagger is None:
            if self.action() != "pop":
                return 1.0
            stagger = a["pop_stagger_s"]
        p = progress(t, index * stagger, a["pop_s"])
        return ease_out_back(p) if p > 0 else 0.0
