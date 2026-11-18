# Shorts Agent

A LangGraph agent that turns a transcript or video description (a `.txt` file) into a
10–20 second vertical stick-figure video (YouTube Shorts / Instagram Reels).

Output: `output/<run_id>/short.mp4` at 1080x1920, 30 fps, with narration.

## Hard constraints (never break these)

- **No paid APIs.** Never import the `anthropic` SDK or any hosted video/TTS API.
- The only LLM access is Claude Code headless mode, wrapped in `src/shorts/llm.py`:
  `claude -p "<prompt>" --output-format json` → read the `result` field.
- Claude is called **only** in the `director` node. Every other node is plain,
  deterministic Python. Same plan in → same video out.
- Text-to-speech is offline: Piper first, pyttsx3 as fallback.
- All visual values (colors, sizes, fonts, timing) come from `config/style.json`.
  Never hardcode them in code.

## Architecture

```
transcript.txt
   │
   ▼
director ──► validate ──(invalid, attempts < 3)──► director
                │
             (valid)
                ▼
             narrate ──► render ──► compose ──► short.mp4
```

| Node | Job | Uses Claude? |
|---|---|---|
| director | Transcript → `VideoPlan` JSON, following the `scene-director` skill | Yes |
| validate | Parse JSON with Pydantic; on error, store the message for a retry | No |
| narrate | One TTS audio file per scene; measure each duration | No |
| render | Draw each scene's frames (stick figures, captions, bubbles) | No |
| compose | Join scene clips + audio into the final MP4 | No |

Scene duration = narration duration + `timing.pad_after_narration_s`, or the
length of the scene's move timeline for `action` scenes, whichever is longer.
Silent scenes (no narration) get a silent WAV of that length, so `compose` treats
every scene the same. That is why `narrate` runs before `render`.

The plan's `audio_mode` (`narrated` | `silent` | `mixed`) is chosen by the
director from the story; `validate` enforces each mode's rules, and
`render/choreo.py` checks fight timing and range by simulating the moves.

If a run is started with `--plan path/to/plan.json`, the graph skips `director`
and goes straight to `validate`. Use this to re-render without using Claude.

## Project layout

```
src/shorts/
  models.py        # Pydantic: VideoPlan, Scene, Character
  state.py         # LangGraph state TypedDict
  llm.py           # call_claude() wrapper around `claude -p`
  graph.py         # builds and compiles the graph
  run.py           # CLI entry: python -m shorts.run input/x.txt [--plan p.json]
  nodes/           # director.py validate.py narrate.py render.py compose.py
  render/          # drawing, all deterministic:
                   #   scene.py     picks a layout and draws one frame
                   #   layouts.py   one render function per scene layout
                   #   poses.py figure.py   pose library + stick figure
                   #   captions.py bubbles.py props.py   text, bubbles, prop catalog
                   #   moves.py     timed keyframe moves (run, flop, punch, ...)
                   #   action.py    draws "action" scenes (trails, impact flash, shake)
                   #   choreo.py    builds and checks fight choreography
                   #   motion.py    easing helpers
                   #   sheets.py    debug contact sheets (output/debug/*.png)
config/style.json  # single source of truth for the look
assets/fonts/      # caption font (.ttf)
assets/voices/     # Piper voice model
input/             # transcripts
output/<run_id>/   # plan.json, audio/, short.mp4, debug/
tests/             # fixtures/plan_*.json + one test per node, move and rule
```

## Skills in this project

| Skill | Use it when |
|---|---|
| `video-style` | Anything about how the video looks or is paced |
| `scene-director` | Writing the director prompt, the `VideoPlan` schema, or planning a video |
| `stick-figure-renderer` | Anything in `src/shorts/render/`, or the render/compose nodes |
| `langgraph-pipeline` | State, nodes, edges, retries, running and debugging the graph |

The `director` node reads `.claude/skills/scene-director/SKILL.md` and
`.claude/skills/video-style/SKILL.md` from disk and puts them into its prompt.
Do not rely on automatic skill loading inside the pipeline; pass them explicitly.

## Milestones (build in this order, one at a time)

1. **Kinetic text.** Hardcoded `tests/fixtures/plan_example.json` → narrate →
   captions on plain backgrounds → MP4. No Claude, no figures.
2. **Stick figures.** Pose library, figures, speech bubbles. Add a pose contact sheet
   at `output/debug/poses.png` for visual checks.
3. **Director.** `llm.py`, director + validate nodes, retry loop (max 3 attempts).
4. **Polish.** Idle animation, caption pop-in, optional background music.
5. **Variety.** Keep the style fixed but let each video show its own subject:
   scene `layout` (dialogue, closeup, big_number, versus, timeline), in-scene
   `action` (enter_left, pose_change, pop, count_up), and `props` drawn from a
   small catalog. Every video uses at least 3 layouts, never the same layout twice
   in a row. One render function per layout, picked from a dict.
6. **Action.** Smooth full-body motion and stick fights.
   - Part 1, movement: a move library (`render/moves.py`) of timed keyframes with
     easing, anticipation and follow-through; motion paths (travel, jump arcs);
     whole-body rotation; motion trails. Test case: the Fosbury flop.
   - Part 2, fighting moves: stance, punch, kick, block, dodge, slash, hit-react,
     knockback, fall; impact flash and screen shake; a sword held in the hand.
   - Part 3, choreography: an `action` layout whose scenes hold a timed list of
     moves per character, validated for timing and range. The director also picks
     the video's `audio_mode` (`narrated` | `silent` | `mixed`) from the story;
     silent scenes get no TTS and their length comes from the move timeline.
     This stays inside the `director` node (Claude is still called only there).
   - Part 4, tests and visual checks: one test per move and rule; render the
     Fosbury flop and a short fight.

## How to work in this repo

- The user is learning agent building. After each change, explain briefly what you
  did and why. Keep code simple, typed, and commented where the reason isn't obvious.
- Work on one milestone at a time. Finish it, run it, then stop and summarize.
- Every node gets a test that runs without calling Claude (use the fixture plan).
- Nodes return partial state dicts and only write files inside `output/<run_id>/`.
- Run: `python -m shorts.run input/example.txt`
- Test: `pytest -q`
