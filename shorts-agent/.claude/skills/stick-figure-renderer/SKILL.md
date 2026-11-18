---
name: stick-figure-renderer
description: How to draw stick figures, captions and speech bubbles with Pillow and assemble scenes into a vertical MP4 with MoviePy. Use for any work in src/shorts/render/ or the narrate, render and compose nodes.
---

# Stick-figure renderer

Everything here is deterministic Python. No LLM calls, no network.
All sizes and colors come from `config/style.json` (see the `video-style` skill).

## Libraries

- Pillow for drawing frames (`ImageDraw.line`, `ellipse`, `rounded_rectangle`).
- MoviePy (2.x) to turn frames + audio into clips and concatenate them.
- Piper TTS (offline) for narration; pyttsx3 as a fallback. Save WAV per scene.
- Measure audio length with `soundfile` or MoviePy's `AudioFileClip.duration`.

## Poses are data, not code

`render/poses.py` defines each pose as joint positions in a unit box
(0–1, origin at the feet, y up). One dict per pose:

```python
POSES = {
    "stand": {"head": (0.5, 0.86), "neck": (0.5, 0.75), "hip": (0.5, 0.42),
              "l_hand": (0.36, 0.48), "r_hand": (0.64, 0.48),
              "l_foot": (0.40, 0.0), "r_foot": (0.60, 0.0)},
    # wave, point, walk, think, jump, shrug, cheer ...
}
```

Optional elbows and knees (`l_elbow`, `r_knee`, ...) make poses read better;
if missing, draw straight limbs. `facing: "left"` mirrors x around 0.5.
The pose names must match the `Literal` in `models.py` exactly.

`figure.py` has one function: `draw_figure(draw, pose, x, ground_y, height, style)`.
It scales the unit pose, then draws head circle + lines with round caps.

## Props are data-driven too

`render/props.py` draws each prop kind (shark, tree, brain, clock, question, arrow,
star) with a small `_draw_<kind>(pen)` function in a unit box (y up, like poses).
`PROP_DRAWERS` maps kind → function. Sizes are `props.size_ratio` × figure height.
Props use the ink color and figure line width; only the star uses the accent.
To add a prop: name in `PROP_KINDS` (models.py) → drawer in `PROP_DRAWERS` → skill.

## Rendering a scene

`scene.py` (`SceneRenderer`) renders one scene into frames:

1. Fill the background color.
2. Call the layout's function from `layouts.LAYOUT_RENDERERS[scene["layout"]]`.
   Never branch on layout names anywhere else; one function per layout:
   - `dialogue`: figures and props on the ground line (the classic look).
   - `closeup`: one figure scaled to fill the space below the caption.
   - `big_number`: the number large and centered, `unit` under it, figure small.
   - `versus`: split screen, a prop + label per side, a "VS" badge on the divider.
   - `timeline`: a time arrow, props popping in left to right, labels below.
3. Draw the caption (`captions.py`) last: wrap, center, accent the `*starred*`
   word, pop in over the first frames.

Speech bubbles (`bubbles.py`) are drawn by the layouts that allow them, above the
speaker's head, tail aimed at the head.

## Motion

All motion is a function of time `t`; easing helpers live in `render/motion.py`.
Timings come from `style.json` `actions`.
- Idle bob on every figure (sine, `figure.idle_period_s`, `figure.idle_lift`).
- `enter_left`: figures walk in from off-screen (walk pose), then take their pose;
  the bubble appears once they arrive.
- `pose_change`: blend `pose` → `end_pose` joint by joint (`lerp_pose`).
- `pop`: props scale in with a small overshoot, one after another.
- `count_up`: the big number counts from 0 over `count_up_share` of the scene.
Round animated values (lift in px, pop scale) so cached layers get reused.

## Moves (full-body action)

`render/moves.py` makes figures run, jump, flip and fight. Moves are data too:

- A `Move` is a list of `Key`s: time `t` (seconds after the move starts), `pose`,
  forward travel `dx` and height `dy` (figure heights), body rotation `rot`
  (degrees around the hip, + leans backward), and `ease` / `ease_y`.
- Smoothness comes from easing, not more keys: rise with `ease_y="out"` (slows
  at the top), fall with `"in"` (speeds up), snap hits with `"back"`.
- Build anticipation and follow-through into the keys: crouch before a jump,
  absorb with bent knees after landing, then settle.
- Travel moves (`walk`, `run`) are one evenly spaced cycle (`cycle_dx`, `period`)
  repeated until the figure reaches `to_x`; strides stretch to land exactly.
- `turned=True` keys face the other way (the flop's back to the bar).
- `trail=True` keys get motion trails (faded copies of the last frames). Mark
  only flight and swing phases; trails on runs just look blurry.
- Poses used only inside moves live in `MOVE_POSES`; `"name~"` swaps left/right
  joints for the other half of a stride.
- A `Track` chains `Step`s for one character; `state(t)` returns the rotated
  pose, x and height. `render/action.py` draws it with trails.
- Check every move change visually: `python -m shorts.render.moves --demo
  fosbury` (also `fight`, `jump`, `backflip`) writes an onion-skin sheet, a
  filmstrip and an MP4 to `output/debug/`. Look at them before moving on.

## Fights

- Fight poses use `r_` for the lead side (toward the opponent), `l_` for the rear.
  `mirror()` swaps the names, so always look up the lead joint with
  `side_joint("r_hand", facing)` (impacts and the sword do this).
- Strikes (`punch`, `kick`, `slash`) follow wind-up → strike (`ease="back"`) →
  short hold → back to `stance`. The strike key carries `impact=<joint>`
  (`"sword"` = blade tip).
- `REACTIONS` (`block` 1, `hit_react` 2, `knockback` 3) decide what an impact looks
  like. An impact only flashes if the other fighter starts a reaction at that
  moment (within 0.15 s); a `dodge` or a miss shows nothing. Strength ≥ 2 also
  shakes the screen (`action.impact`).
- `ActionScene` draws all `Actor`s (track + color + `holds`), trails, the sword
  (along the lead forearm), flashes, then the shake. Fighters bob lightly in
  their guard while holding still.
- Range matters: a punch reaches ~0.6 figure heights from the attacker's
  origin, a kick ~0.55, a slash ~0.9. Check impact x against the defender's x.

Frame count = round(scene_duration × fps). Frames are generated on demand by a
MoviePy `VideoClip(frame_function)`: holding every full-HD frame in memory
(`ImageSequenceClip`) costs ~1 GB per scene.

## Compose

- For each scene: clip.with_audio(scene_audio).
- `concatenate_videoclips(clips, method="chain")` — hard cuts.
- Export: `write_videofile(path, fps=30, codec="libx264", audio_codec="aac")`.

## Visual checks (do these, don't skip them)

- `python -m shorts.render.poses --sheet` writes three contact sheets to
  `output/debug/`: `poses.png` (every pose), `props.png` (every prop) and
  `layouts.png` (every layout, mid-action and at the end). Open them and look
  after any change to poses, props or layouts.
- `--debug` on a run also saves the last frame of every scene to `debug/`.
- Draw the safe zone as a thin red outline in debug mode only.

## Common mistakes

- Pillow's y axis points down; poses use y up. Convert in one place only.
- Fonts: load the `.ttf` from `assets/fonts/`; never rely on system fonts.
- Keep the final video at even dimensions (1080x1920 is fine) for libx264.
