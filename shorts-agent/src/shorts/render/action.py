"""Draws action scenes: moving figures (Tracks) with trails, swords and hit effects.

An ActionScene holds a few Actors (a Track + a color + what they hold). For each
frame it draws every actor, then impact flashes, then shakes the frame on a hit.
Also has debug demos: `python -m shorts.render.moves --demo fight`.
"""

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from shorts.render.figure import render_figure
from shorts.render.moves import REACTIONS, Step, Track, side_joint
from shorts.render.poses import PoseDict, lifted
from shorts.render.props import render_prop
from shorts.style import ROOT, hex_to_rgb, load_style

RGB = tuple[int, int, int]

# Screen-shake offsets, scaled down frame by frame (deterministic, no randomness).
_SHAKE_PATTERN = [(1, -1), (-1, 1), (1, 1), (-1, -1)]


def action_height(style: dict) -> int:
    """Figure height in action scenes (smaller, so there's room to move)."""
    return int(style["figure"]["height_px"] * style["action"]["figure_scale"])


@dataclass
class Actor:
    track: Track
    color: RGB
    holds: str | None = None  # "sword" or None


@dataclass(frozen=True)
class Impact:
    frame: int
    x: float
    y: float
    strength: int  # 1 block, 2 hit, 3 knockback (see moves.REACTIONS)


def _joint_px(pose: PoseDict, x: float, y: float, ground: float, height: int, joint: str) -> tuple[float, float]:
    jx, jy = pose[joint]
    return (x + (jx - 0.5) * height, ground - y - jy * height)


def _sword_points(pose: PoseDict, x: float, y: float, ground: float, height: int, style: dict,
                  facing: str):
    """(pommel, guard_a, guard_b, tip) in pixels: the blade follows the lead forearm."""
    hand = _joint_px(pose, x, y, ground, height, side_joint("r_hand", facing))
    elbow = _joint_px(pose, x, y, ground, height, side_joint("r_elbow", facing))
    dx, dy = hand[0] - elbow[0], hand[1] - elbow[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    s = style["action"]["sword"]
    length, guard = s["length"] * height, s["guard"] * height
    gx, gy = hand[0] + ux * guard * 0.6, hand[1] + uy * guard * 0.6
    return ((hand[0] - ux * guard * 0.6, hand[1] - uy * guard * 0.6),
            (gx - uy * guard, gy + ux * guard), (gx + uy * guard, gy - ux * guard),
            (hand[0] + ux * length, hand[1] + uy * length))


def _draw_sword(img: Image.Image, points, style: dict, color: RGB, alpha: float) -> None:
    pommel, ga, gb, tip = points
    lw = style["figure"]["line_width"]
    ss = style["figure"]["supersample"]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, y0 = int(min(xs)) - lw, int(min(ys)) - lw
    w, h = int(max(xs)) - x0 + 2 * lw, int(max(ys)) - y0 + 2 * lw
    layer = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def p(pt):
        return ((pt[0] - x0) * ss, (pt[1] - y0) * ss)

    blade = max(2, int(lw * 0.6)) * ss
    d.line([p(pommel), p(tip)], fill=color, width=blade)
    d.line([p(ga), p(gb)], fill=color, width=lw * ss)
    layer = layer.resize((w, h), Image.LANCZOS)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(layer, (x0, y0), layer)


def _paste_figure(img: Image.Image, pose: PoseDict, x: float, y: float, ground: float, height: int,
                  style: dict, color: RGB, alpha: float = 1.0) -> None:
    layer, foot = render_figure(pose, height, style, color)
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(layer, (int(x - foot[0]), int(ground - y - foot[1])), layer)


class ActionScene:
    """Everything that moves in an action scene, drawn frame by frame."""

    def __init__(self, actors: list[Actor], ground: float, style: dict, bg: RGB, accent: RGB):
        self.actors, self.ground, self.style = actors, ground, style
        self.bg, self.accent = bg, accent
        self.fps = style["canvas"]["fps"]
        self.impacts = self._find_impacts()

    def _state(self, actor: Actor, frame: int):
        # Whole frame indices, so trail ghosts reuse figures cached on earlier frames.
        t = max(0, frame) / self.fps
        pose, x, y = actor.track.state(t)
        if actor.track.holding(t) and pose["head"][1] > pose["hip"][1]:
            # Fighters bounce lightly in their guard instead of freezing.
            a = self.style["action"]
            wave = (math.sin(2 * math.pi * t / a["guard_period_s"]) + 1) / 2
            pose = lifted(pose, -round(wave * a["guard_bob"] * actor.track.height) / actor.track.height)
        return pose, x, y

    def _find_impacts(self) -> list[Impact]:
        """A strike only "lands" (flash, shake) if someone reacts to it at that moment."""
        found = []
        for actor in self.actors:
            for t, joint in actor.track.impacts:
                reacting = [(REACTIONS[r], o) for o in self.actors if o is not actor
                            if (r := o.track.reaction_at(t))]
                if not reacting:
                    continue  # a dodge or a miss: no effect
                strength, defender = max(reacting, key=lambda pair: pair[0])
                px, py = self.strike_point(actor, t, joint)
                # A blade passes through its target: flash where it meets the body.
                x = actor.track.state(t)[1]
                body_x = defender.track.state(t)[1]
                if (px - body_x) * (body_x - x) > 0:
                    px = body_x
                found.append(Impact(round(t * self.fps), px, py, strength))
        return found

    def strike_point(self, actor: Actor, t: float, joint: str) -> tuple[float, float]:
        """Pixel position of the striking fist/foot/blade tip at time t."""
        pose, x, y = actor.track.state(t)
        h = actor.track.height
        if joint == "sword":
            return _sword_points(pose, x, y, self.ground, h, self.style, actor.track.facing_at(t))[3]
        return _joint_px(pose, x, y, self.ground, h, joint)

    def _draw_actor(self, img: Image.Image, actor: Actor, frame: int) -> None:
        a = self.style["action"]
        h = actor.track.height
        ghosts = []
        if frame > 0 and actor.track.trailing(frame / self.fps):
            n = a["trail_frames"]
            ghosts = [(frame - k, a["trail_alpha"] * (n + 1 - k) / (n + 1)) for k in range(n, 0, -1)]
        for f, alpha in ghosts + [(frame, 1.0)]:  # oldest (faintest) first, then the figure
            pose, x, y = self._state(actor, f)
            _paste_figure(img, pose, x, y, self.ground, h, self.style, actor.color, alpha)
            if actor.holds == "sword":
                facing = actor.track.facing_at(max(0, f) / self.fps)
                _draw_sword(img, _sword_points(pose, x, y, self.ground, h, self.style, facing),
                            self.style, actor.color, alpha)

    def _draw_flash(self, img: Image.Image, impact: Impact, age: int) -> None:
        cfg = self.style["action"]["impact"]
        p = age / cfg["flash_frames"]
        radius = cfg["flash_radius"] * self.actors[0].track.height * (0.5 + 0.25 * impact.strength)
        lw = self.style["figure"]["line_width"]
        draw = ImageDraw.Draw(img)
        # A ring of spikes that bursts outward and thins away.
        for k in range(cfg["flash_spikes"]):
            ang = 2 * math.pi * k / cfg["flash_spikes"] + 0.3
            r0, r1 = radius * (0.25 + 0.6 * p), radius * (0.6 + 0.6 * p)
            draw.line([(impact.x + r0 * math.cos(ang), impact.y + r0 * math.sin(ang)),
                       (impact.x + r1 * math.cos(ang), impact.y + r1 * math.sin(ang))],
                      fill=self.accent, width=max(2, int(lw * (1 - 0.6 * p))))

    def _shake(self, frame: int) -> tuple[int, int]:
        cfg = self.style["action"]["impact"]
        for impact in self.impacts:
            age = frame - impact.frame
            if impact.strength >= 2 and 0 <= age < cfg["shake_frames"]:
                amp = cfg["shake_px"] * (impact.strength - 1) * (1 - age / cfg["shake_frames"])
                sx, sy = _SHAKE_PATTERN[age % len(_SHAKE_PATTERN)]
                return int(sx * amp), int(sy * amp)
        return 0, 0

    def draw(self, img: Image.Image, frame: int) -> Image.Image:
        """Draw onto `img` (background and props already there). Returns the shaken frame."""
        for actor in self.actors:
            self._draw_actor(img, actor, frame)
        for impact in self.impacts:
            age = frame - impact.frame
            if 0 <= age < self.style["action"]["impact"]["flash_frames"]:
                self._draw_flash(img, impact, age)
        dx, dy = self._shake(frame)
        if dx or dy:
            shaken = Image.new("RGB", img.size, self.bg)
            shaken.paste(img, (dx, dy))
            return shaken
        return img

    @property
    def end_time(self) -> float:
        return max(a.track.end_time for a in self.actors)


def draw_ground(img: Image.Image, ground: float, style: dict, ink: RGB) -> None:
    lw = max(2, style["figure"]["line_width"] // 2)
    ImageDraw.Draw(img).line([(0, ground), (img.width, ground)], fill=ink, width=lw)


# --- demos (debug only) ---------------------------------------------------------

def fosbury_demo(style: dict, ink: RGB, accent: RGB):
    """Run-up and Fosbury flop over a bar. Returns (actors, props, duration)."""
    w = style["canvas"]["width"]
    height = action_height(style)
    takeoff_x = 0.28 * w
    track = Track(x=-0.4 * height, facing="right", height=height, steps=[
        Step("run", to_x=takeoff_x),
        Step("flop"),
    ])
    # (kind, center x, size): bar where the hips peak, mat where the body lands.
    props = [("mat", takeoff_x + 1.45 * height, int(height * 1.1)),
             ("bar", takeoff_x + 0.95 * height, height)]
    return [Actor(track, ink)], props, track.end_time + 0.6


def fight_demo(style: dict, ink: RGB, accent: RGB):
    """Sword fighter (ink) vs boxer (accent): clash, punch, dodge, finishing slash."""
    w = style["canvas"]["width"]
    height = action_height(style)
    a = Track(x=0.08 * w, facing="right", height=height, steps=[
        Step("stance", at=0.0),
        Step("run", at=0.3, to_x=0.43 * w),
        Step("slash", at=0.75),       # blade lands at 0.99 -> B blocks
        Step("hit_react", at=1.67),   # B's punch lands at 1.67
        Step("dodge", at=2.30),       # B's kick (lands 2.52) misses
        Step("slash", at=3.05),       # lands at 3.29 -> B is knocked back
    ])
    b = Track(x=0.62 * w, facing="left", height=height, steps=[
        Step("stance", at=0.0),
        Step("block", at=0.92),
        Step("punch", at=1.50),       # lands at 1.67
        Step("kick", at=2.30),        # lands at 2.52
        Step("knockback", at=3.29),
    ])
    actors = [Actor(a, ink, holds="sword"), Actor(b, accent)]
    return actors, [], max(a.end_time, b.end_time) + 0.8


def _single_move_demo(move: str, start_x: float, walk_in: bool = True):
    def demo(style: dict, ink: RGB, accent: RGB):
        w = style["canvas"]["width"]
        height = action_height(style)
        steps = ([Step("walk", to_x=start_x * w)] if walk_in else []) + [Step(move)]
        track = Track(x=0.12 * w, facing="right", height=height, steps=steps)
        return [Actor(track, ink)], [], track.end_time + 0.5
    return demo


DEMOS = {
    "fosbury": fosbury_demo,
    "fight": fight_demo,
    "jump": _single_move_demo("jump", 0.35),
    "backflip": _single_move_demo("backflip", 0.55),
}


def _demo_frame_fn(name: str, style: dict):
    colors = style["colors"]
    ink, accent = hex_to_rgb(colors["ink"]), hex_to_rgb(colors["accent"])
    bg = hex_to_rgb(colors["backgrounds"]["white"])
    actors, props, duration = DEMOS[name](style, ink, accent)
    ground = int(style["canvas"]["height"] * style["figure"]["ground_y"])
    lw = style["figure"]["line_width"]
    base = Image.new("RGB", (style["canvas"]["width"], style["canvas"]["height"]), bg)
    draw_ground(base, ground, style, ink)
    for kind, cx, size in props:
        layer = render_prop(kind, size, style, ink, accent)
        base.paste(layer, (int(cx - layer.width / 2), int(ground - layer.height + lw)), layer)
    scene = ActionScene(actors, ground, style, bg, accent)

    def frame(i: int) -> Image.Image:
        return scene.draw(base.copy(), i)

    return frame, base, scene, ground, duration


def write_demo(name: str) -> list[Path]:
    """Onion-skin sheet, filmstrip and an MP4 of a demo, in output/debug/."""
    from moviepy import VideoClip

    style = load_style()
    fps = style["canvas"]["fps"]
    frame, base, scene, ground, duration = _demo_frame_fn(name, style)
    n_frames = round(duration * fps)
    height = scene.actors[0].track.height
    out_dir = ROOT / "output" / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    band = (0, int(ground - 2.2 * height), base.width, int(ground + 0.3 * height))

    # Onion skin: every 3rd frame on one canvas, older = fainter. Shows the motion arc.
    onion = base.copy()
    picks = list(range(0, n_frames, 3))
    for j, i in enumerate(picks):
        for actor in scene.actors:
            pose, x, y = actor.track.state(i / fps)
            _paste_figure(onion, pose, x, y, ground, height, style, actor.color,
                          alpha=0.15 + 0.85 * (j + 1) / len(picks))
    onion_path = out_dir / f"move_{name}_onion.png"
    onion.crop(band).save(onion_path)

    # Filmstrip: every 4th frame, cropped to the action band, timestamped.
    picks = list(range(0, n_frames, 4))
    s = 0.4
    tw, th = int((band[2] - band[0]) * s), int((band[3] - band[1]) * s)
    cols = 4
    strip = Image.new("RGB", (cols * (tw + 8) + 8, math.ceil(len(picks) / cols) * (th + 8) + 8), (110, 110, 110))
    d = ImageDraw.Draw(strip)
    for j, i in enumerate(picks):
        x, y = 8 + (j % cols) * (tw + 8), 8 + (j // cols) * (th + 8)
        strip.paste(frame(i).crop(band).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 6, y + 4), f"{i / fps:.2f}s", fill=(200, 60, 40))
    strip_path = out_dir / f"move_{name}_strip.png"
    strip.save(strip_path)

    clip = VideoClip(lambda t: np.asarray(frame(min(round(t * fps), n_frames - 1))), duration=duration)
    mp4_path = out_dir / f"move_{name}.mp4"
    clip.write_videofile(str(mp4_path), fps=fps, codec="libx264", audio=False,
                         ffmpeg_params=["-pix_fmt", "yuv420p"], logger=None)
    clip.close()
    return [onion_path, strip_path, mp4_path]
