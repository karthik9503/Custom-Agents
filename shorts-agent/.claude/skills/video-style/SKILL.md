---
name: video-style
description: Visual look and pacing rules for the stick-figure shorts. Use when writing or changing rendering, captions, colors, layout or timing, or when planning scenes so they match the house style.
---

# Video style: clean whiteboard stick figures

The numbers live in `config/style.json`. This file explains the look in words so
code and plans stay consistent. If the two disagree, `style.json` wins for numbers.

## The look in one sentence

Thick black stick figures on a flat background, one bold caption per scene, and a
single orange accent color used only for emphasis.

## Canvas and safe zones

- Vertical 1080x1920, 30 fps.
- Shorts and Reels cover parts of the screen with buttons and text. Keep all
  captions and faces inside the safe zone from `style.json` (`safe_zone`):
  roughly the top 12%, the bottom 20% and the right 14% stay free of anything important.
- Figures stand on an invisible ground line in the lower-middle of the safe zone.
- The caption sits in the upper-middle (`caption.y`), above the figures.

## Figures

- Head is a circle; body, arms and legs are single thick lines with round caps.
- Line width from `figure.line_width`. Figures share one size, except in the
  `closeup` (bigger) and `big_number` (smaller) layouts.
- Ink color is `colors.ink`; on the `night` background use `colors.ink_on_night`.
- At most 3 figures per scene, spread out so they never overlap.
- A figure can be highlighted (e.g. the one speaking) by drawing its head outline
  in `colors.accent`. Use this sparingly.

## Captions

- One caption per scene, 1–6 words, at most 2 lines, centered.
- Bold font from `caption.font`, size `caption.size_px`.
- The caption is the key phrase of the scene, not the full narration.
- Pop in over `caption.pop_in_frames` frames (scale 90% → 100% with fade).
- At most one word per caption may be colored `colors.accent`, marked in the plan
  as `*word*`.

## Layouts

The caption always sits at `caption.y`; the layout decides everything below it.

- **dialogue**: figures (and props) stand side by side on the ground line. The
  everyday layout for people talking or reacting.
- **closeup**: one figure, scaled up to fill the space under the caption. For a
  strong reaction or a direct question to the viewer.
- **big_number**: one number, very large and centered, with a short unit under it;
  at most one small figure off to the side. The number is the star of the scene.
- **versus**: a split screen with a thin divider and a "VS" badge; one prop and one
  label per side. For comparisons.
- **timeline**: a horizontal arrow with ticks; 2–3 props appear above it left to
  right, labels below. For things that happen in order.

- **action**: smaller figures (`action.figure_scale`) on a visible ground line,
  moving through the scene: running, jumping, flipping, fighting. Fast phases
  leave faint motion trails; a landed hit flashes an accent starburst and shakes
  the screen. Fighters wear different colors (`ink` vs `accent`). A sword is a
  thin blade along the hand's forearm.

Vary the layout from scene to scene so every cut changes the picture.

## Sound

- `narrated`: a voice in every scene. `silent`: no voice and no captions needed,
  the action tells the story. `mixed`: voice for the setup and payoff, silence for
  the action moment in between.

## Props

- Simple line drawings of the topic's objects, in the same ink and line width as
  the figures. Only the star is filled, with the accent.
- Sizes `small`, `medium`, `large` are fractions of the figure height
  (`props.size_ratio`); a large prop is as tall as a figure.

## Speech bubbles

- Optional, rounded rectangles with a small tail pointing at the speaker's head.
- Max `bubble.max_chars` characters. Never more than one bubble per scene.

## Motion and pacing

- Total length 10–20 s; each scene 2–5 s (`timing`).
- The first scene is the hook: it must make sense within 2 seconds.
- Figures always have a gentle idle bob. On top of that, one action per scene
  (`actions` in `style.json`): a figure walks in from the left, a pose changes,
  props pop in, or a number counts up. No camera moves.
- Hard cuts between scenes. No wipes, spins or fancy transitions.
- The last scene ends with a clear payoff or punchline, and the final pose matches
  its mood (not always a cheer).

## Don't

- No gradients, shadows, textures or extra colors.
- No text smaller than the bubble font.
- No figures or text outside the safe zone.

## Changing the style

To change the look, edit `config/style.json` for numbers and colors, and update this
file for the rules in words. Then re-render an existing run with `--plan` to compare.
