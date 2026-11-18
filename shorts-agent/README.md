# Shorts Agent: starter kit

Instructions (`CLAUDE.md`) and skills (`.claude/skills/`) for building a LangGraph agent
that turns a transcript into a 10–20 second stick-figure short, using Claude Code in VS Code.

## What's in here

| Path | What it is |
|---|---|
| `CLAUDE.md` | Project rules Claude Code reads every session: architecture, constraints, milestones |
| `.claude/skills/video-style/` | The look: colors, safe zones, captions, pacing |
| `.claude/skills/scene-director/` | How to turn a transcript into a `VideoPlan` JSON (also used by the pipeline at runtime) |
| `.claude/skills/stick-figure-renderer/` | How to draw poses, captions, bubbles and assemble the MP4 |
| `.claude/skills/langgraph-pipeline/` | State, nodes, edges, retry loop, calling `claude -p` |
| `config/style.json` | All numbers for the look. Edit this to change the style |
| `tests/fixtures/plan_example.json` | A ready-made plan so you can build without calling Claude |
| `input/example.txt` | A sample transcript |

## Setup (once)

1. Unzip this folder and open it in VS Code (File → Open Folder).
2. Create a virtual environment and install packages:
   ```
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS / Linux
   pip install -r requirements.txt
   pip install -e .              # makes `python -m shorts.run` work from anywhere
   ```
3. ffmpeg: MoviePy uses the copy bundled with `imageio-ffmpeg`, so a system install
   is optional.
4. Download a Piper voice (e.g. `en_US-lessac-medium.onnx` + its `.json`) into
   `assets/voices/`, and put a bold `.ttf` font at `assets/fonts/caption-bold.ttf`.
5. Make sure `claude -p "say hi"` works in the terminal and is logged in with your
   Pro/Max plan (run `claude login` if not).
6. Start Claude Code in the VS Code terminal or extension, from this folder. Type `/` to
   check that the four skills are listed. If not, restart Claude Code.

## Prompts to paste into Claude Code, one milestone at a time

**Milestone 1 — kinetic text (no Claude, no figures)**
> Read CLAUDE.md. Build milestone 1: models.py, state.py, the narrate, render and
> compose nodes, graph.py and run.py, so that
> `python -m shorts.run input/example.txt --plan tests/fixtures/plan_example.json`
> produces a short with captions on colored backgrounds and narration. Skip figures
> for now. Add tests, run them, then explain what you built.

**Milestone 2 — stick figures**
> Build milestone 2 using the stick-figure-renderer skill: the pose library, figures
> and speech bubbles. Generate the pose contact sheet and show me the image before
> wiring figures into the scene renderer.

**Milestone 3 — the director**
> Build milestone 3: llm.py, the director and validate nodes and the retry loop, using
> the langgraph-pipeline and scene-director skills. Then run the full pipeline on
> input/example.txt without --plan.

**Milestone 4 — polish**
> Build milestone 4: idle animation and caption pop-in as described in video-style.

**Milestone 5 — variety**
> Build milestone 5: scene layouts (dialogue, closeup, big_number, versus, timeline),
> in-scene actions (enter_left, pose_change, pop, count_up) and a small prop catalog.
> One render function per layout, picked from a dict. Validate that every video uses
> at least 3 layouts and never the same layout twice in a row. Render a layout contact
> sheet at `output/debug/layouts.png` and show it to me.

**Milestone 6 — action**
> Build milestone 6 in its four parts (see CLAUDE.md): a move library with easing and
> motion paths (test: the Fosbury flop), fighting moves with impact effects and a sword,
> an `action` layout with timed moves per character and checked choreography, and the
> director's `audio_mode` choice (narrated, silent, mixed). Add a test per move and
> rule, then render `input/fosbury.txt` and `input/fight.txt`.

## Status

All six milestones are built and tested (`pytest -q`). Sample transcripts in
`input/` cover each audio mode: narrated (`example`, `shark`, `octopus`), mixed
(`fosbury`, `long_jump`) and silent (`fight`, `rooftop_rivals`).

## Changing the style

The style is split in two on purpose:
- **Numbers and colors** → `config/style.json`. The renderer reads them, so the change
  shows up in every video. Example: make `accent` blue, or `line_width` thicker.
- **Rules in words** → `.claude/skills/video-style/SKILL.md`. The director reads this,
  so it plans scenes that fit the style. Example: "always end on a cheer pose".

Then re-render an old run with `--plan output/<run_id>/plan.json` to compare, with
no Claude usage.
