"""Pose library. Poses are data: joint positions in a unit box.

Coordinates: x 0-1 (0.5 is the body's center line), y 0-1 with the origin at
the feet and y pointing UP. figure.py converts to Pillow's y-down pixels.
"l_"/"r_" mean screen-left/right for a figure facing right.

Run `python -m shorts.render.poses --sheet` to draw a contact sheet.
"""

import argparse
from typing import get_args

Joint = tuple[float, float]
PoseDict = dict[str, Joint]

# Torso joints shared by most poses.
_HEAD, _NECK, _HIP = (0.5, 0.86), (0.5, 0.73), (0.5, 0.42)
_LEGS: PoseDict = {
    "l_knee": (0.45, 0.21), "l_foot": (0.40, 0.0),
    "r_knee": (0.55, 0.21), "r_foot": (0.60, 0.0),
}
_L_ARM_DOWN: PoseDict = {"l_elbow": (0.42, 0.58), "l_hand": (0.38, 0.44)}
_R_ARM_DOWN: PoseDict = {"r_elbow": (0.58, 0.58), "r_hand": (0.62, 0.44)}

POSES: dict[str, PoseDict] = {
    "stand": {"head": _HEAD, "neck": _NECK, "hip": _HIP,
              **_L_ARM_DOWN, **_R_ARM_DOWN, **_LEGS},
    "wave": {"head": _HEAD, "neck": _NECK, "hip": _HIP,
             **_L_ARM_DOWN,
             "r_elbow": (0.73, 0.78), "r_hand": (0.77, 0.96),
             **_LEGS},
    "point": {"head": _HEAD, "neck": _NECK, "hip": _HIP,
              **_L_ARM_DOWN,
              "r_elbow": (0.67, 0.70), "r_hand": (0.84, 0.72),
              **_LEGS},
    "walk": {"head": (0.53, 0.86), "neck": (0.52, 0.73), "hip": (0.5, 0.42),
             # Arms swing opposite to the legs.
             "l_elbow": (0.58, 0.59), "l_hand": (0.65, 0.47),
             "r_elbow": (0.43, 0.59), "r_hand": (0.36, 0.47),
             "l_knee": (0.41, 0.22), "l_foot": (0.30, 0.0),
             "r_knee": (0.60, 0.21), "r_foot": (0.68, 0.02)},
    "think": {"head": (0.52, 0.86), "neck": _NECK, "hip": _HIP,
              # Left arm folded across the belly, right hand at the chin.
              "l_elbow": (0.40, 0.57), "l_hand": (0.58, 0.58),
              "r_elbow": (0.64, 0.58), "r_hand": (0.60, 0.74),
              **_LEGS},
    "jump": {"head": (0.5, 0.94), "neck": (0.5, 0.81), "hip": (0.5, 0.50),
             # Whole body in the air, knees tucked, arms flung out.
             "l_elbow": (0.34, 0.86), "l_hand": (0.22, 0.95),
             "r_elbow": (0.66, 0.86), "r_hand": (0.78, 0.95),
             "l_knee": (0.36, 0.30), "l_foot": (0.42, 0.10),
             "r_knee": (0.64, 0.30), "r_foot": (0.58, 0.10)},
    "shrug": {"head": (0.5, 0.85), "neck": (0.5, 0.73), "hip": _HIP,
              # Elbows low and out, palms up beside the shoulders.
              "l_elbow": (0.34, 0.60), "l_hand": (0.26, 0.72),
              "r_elbow": (0.66, 0.60), "r_hand": (0.74, 0.72),
              **_LEGS},
    "cheer": {"head": _HEAD, "neck": _NECK, "hip": _HIP,
              # Arms in a wide V so they clear the head.
              "l_elbow": (0.30, 0.82), "l_hand": (0.22, 0.98),
              "r_elbow": (0.70, 0.82), "r_hand": (0.78, 0.98),
              "l_knee": (0.43, 0.21), "l_foot": (0.36, 0.0),
              "r_knee": (0.57, 0.21), "r_foot": (0.64, 0.0)},
}

# Joints that move with the torso during the idle bob (feet stay planted).
_TORSO = ("head", "neck", "hip", "l_elbow", "l_hand", "r_elbow", "r_hand")
_KNEES = ("l_knee", "r_knee")


def get_pose(name: str, facing: str = "right") -> PoseDict:
    pose = dict(POSES[name])
    if facing == "left":
        pose = mirror(pose)
    return pose


def mirror(pose: PoseDict) -> PoseDict:
    """Flip x around 0.5 and swap left/right joint names."""
    out: PoseDict = {}
    for joint, (x, y) in pose.items():
        if joint.startswith("l_"):
            joint = "r_" + joint[2:]
        elif joint.startswith("r_"):
            joint = "l_" + joint[2:]
        out[joint] = (1.0 - x, y)
    return out


def lifted(pose: PoseDict, amount: float) -> PoseDict:
    """Copy of `pose` with the torso raised by `amount` (knees half as much)."""
    out = dict(pose)
    for joint in _TORSO:
        x, y = out[joint]
        out[joint] = (x, y + amount)
    for joint in _KNEES:
        x, y = out[joint]
        out[joint] = (x, y + amount / 2)
    return out


def write_contact_sheet(path) -> None:
    """Draw every pose side by side with its name, for visual checks."""
    from PIL import Image, ImageDraw, ImageFont

    from shorts.render.figure import render_figure
    from shorts.style import hex_to_rgb, load_style, project_path

    style = load_style()
    fig = style["figure"]
    ink = hex_to_rgb(style["colors"]["ink"])
    bg = hex_to_rgb(style["colors"]["backgrounds"]["white"])
    accent = hex_to_rgb(style["colors"]["accent"])
    font = ImageFont.truetype(str(project_path(style["bubble"]["font"])), style["bubble"]["size_px"])

    height = fig["height_px"]
    names = list(POSES)
    cols = 4
    rows = (len(names) + cols - 1) // cols
    cell_w, cell_h = int(height * 1.0), int(height * 1.45)
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), bg)
    draw = ImageDraw.Draw(sheet)

    for i, name in enumerate(names):
        cx = (i % cols) * cell_w + cell_w // 2
        top = (i // cols) * cell_h
        ground = top + int(cell_h * 0.80)
        layer, foot = render_figure(get_pose(name), height, style, ink)
        sheet.paste(layer, (cx - foot[0], ground - foot[1]), layer)
        draw.line([(cx - cell_w * 0.4, ground), (cx + cell_w * 0.4, ground)], fill=accent, width=2)
        draw.text((cx, ground + 20), name, font=font, fill=ink, anchor="mt")

    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def _main() -> None:
    from shorts.models import Pose
    from shorts.style import ROOT

    from shorts.render.sheets import write_layout_sheet, write_prop_sheet

    parser = argparse.ArgumentParser(description="Pose library tools")
    parser.add_argument("--sheet", action="store_true",
                        help="write poses.png, props.png and layouts.png to output/debug/")
    args = parser.parse_args()

    missing = set(get_args(Pose)) - set(POSES)
    if missing:
        raise SystemExit(f"poses missing from POSES: {sorted(missing)}")
    if args.sheet:
        out_dir = ROOT / "output" / "debug"
        for name, write in (("poses.png", write_contact_sheet), ("props.png", write_prop_sheet),
                            ("layouts.png", write_layout_sheet)):
            write(out_dir / name)
            print(f"wrote {out_dir / name}")


if __name__ == "__main__":
    _main()
