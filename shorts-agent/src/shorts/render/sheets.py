"""Debug contact sheets: every pose, every prop, every layout.

Run `python -m shorts.render.poses --sheet`; it writes all three to output/debug/.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from shorts.models import Scene
from shorts.render.props import PROP_DRAWERS, prop_size_px, render_prop
from shorts.render.scene import SceneRenderer, draw_safe_zone
from shorts.style import hex_to_rgb, load_style, project_path

# One sample scene per layout, each using a different action.
SAMPLE_SCENES: list[dict] = [
    {"narration": "x", "caption": "Two *friends*", "background": "white", "layout": "dialogue",
     "action": "enter_left",
     "characters": [{"id": "a", "pose": "wave", "x": 0.15, "says": "Look at this tree!"},
                    {"id": "b", "pose": "stand", "x": 0.75, "facing": "left"}],
     "props": [{"kind": "tree", "x": 0.45, "size": "large"}]},
    {"narration": "x", "caption": "Wait, *what*?", "background": "night", "layout": "closeup",
     "action": "pose_change",
     "characters": [{"id": "a", "pose": "think", "end_pose": "jump"}]},
    {"narration": "x", "caption": "*450* million", "background": "sky", "layout": "big_number",
     "action": "count_up", "number": 450, "unit": "million years",
     "characters": [{"id": "a", "pose": "point"}]},
    {"narration": "x", "caption": "Who is *older*?", "background": "white", "layout": "versus",
     "action": "pop",
     "props": [{"kind": "shark", "label": "Sharks"}, {"kind": "tree", "label": "Trees"}]},
    {"narration": "x", "caption": "Then *trees*", "background": "sky", "layout": "timeline",
     "props": [{"kind": "shark", "label": "450M"}, {"kind": "tree", "label": "385M"},
               {"kind": "star", "label": "Today"}]},
]


def _font(style: dict, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(project_path(style["bubble"]["font"])), size)


def write_prop_sheet(path: Path) -> None:
    style = load_style()
    ink = hex_to_rgb(style["colors"]["ink"])
    accent = hex_to_rgb(style["colors"]["accent"])
    bg = hex_to_rgb(style["colors"]["backgrounds"]["white"])
    font = _font(style, style["bubble"]["size_px"])

    size = prop_size_px("medium", style)
    cell = int(size * 1.4)
    kinds = list(PROP_DRAWERS)
    sheet = Image.new("RGB", (cell * len(kinds), int(cell * 1.25)), bg)
    draw = ImageDraw.Draw(sheet)
    for i, kind in enumerate(kinds):
        layer = render_prop(kind, size, style, ink, accent)
        cx = i * cell + cell // 2
        sheet.paste(layer, (cx - layer.width // 2, (cell - layer.height) // 2), layer)
        draw.text((cx, cell), kind, font=font, fill=ink, anchor="mt")
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def write_layout_sheet(path: Path, duration: float = 3.0, scale: float = 0.4) -> None:
    """Each layout twice: early in the scene (mid-action) and at the end."""
    style = load_style()
    ink = hex_to_rgb(style["colors"]["ink"])
    font = _font(style, 30)  # sheet header only, not part of any video
    w = int(style["canvas"]["width"] * scale)
    h = int(style["canvas"]["height"] * scale)
    pad, head = 16, 70

    scenes = [Scene.model_validate(s).model_dump() for s in SAMPLE_SCENES]
    sheet = Image.new("RGB", (len(scenes) * (w + pad) + pad, 2 * (h + pad) + head + pad), (128, 128, 128))
    draw = ImageDraw.Draw(sheet)
    for col, scene in enumerate(scenes):
        renderer = SceneRenderer(scene, duration, style)
        x = pad + col * (w + pad)
        draw.text((x + w // 2, head // 2), f"{scene['layout']} / {scene['action']}",
                  font=font, fill=ink, anchor="mm")
        for row, i in enumerate((int(renderer.n_frames * 0.12), renderer.n_frames - 1)):
            frame = renderer.frame(i)
            draw_safe_zone(frame, style)
            sheet.paste(frame.resize((w, h), Image.LANCZOS), (x, head + row * (h + pad)))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
