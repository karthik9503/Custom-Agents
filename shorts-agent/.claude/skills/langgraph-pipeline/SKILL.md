---
name: langgraph-pipeline
description: Conventions for the LangGraph state, nodes, edges and retry loop in this project, plus how to call Claude Code headless from a node. Use when adding or changing nodes, edges, state fields, graph.py, llm.py or run.py, or when debugging a run.
---

# LangGraph pipeline

## State

One `TypedDict` in `state.py`. Every field has a clear owner (the node that writes it).

```python
class ShortState(TypedDict, total=False):
    run_id: str
    run_dir: str             # output/<run_id>
    transcript: str
    raw_plan: str            # director output (text)
    plan: dict               # validated VideoPlan.model_dump()
    error: str | None        # last validation error
    attempts: int            # director attempts so far
    audio_paths: list[str]   # narrate
    durations: list[float]   # narrate, seconds per scene
    clip_paths: list[str]    # render
    video_path: str          # compose
```

## Node rules

- A node is a plain function `(state) -> dict` returning **only** the fields it changed.
- Nodes never call other nodes. Flow lives in `graph.py`, never inside nodes.
- Nodes write files only under `state["run_dir"]`.
- Routing functions only read state and return a node name or `END`.

## Graph

```python
g.add_conditional_edges(START, start_router)       # "director" or "validate" (--plan)
g.add_edge("director", "validate")
g.add_conditional_edges("validate", after_validate) # "narrate" | "director" | END
g.add_edge("narrate", "render")
g.add_edge("render", "compose")
g.add_edge("compose", END)
```

`after_validate`: valid → `"narrate"`; invalid and `attempts < 3` → `"director"`;
otherwise `END` (and `run.py` prints the last error).

## Calling Claude (director only)

```python
import json, subprocess

def call_claude(prompt: str, timeout: int = 180) -> str:
    out = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    return json.loads(out.stdout)["result"]
```

- Build the prompt from: `scene-director` SKILL.md + `video-style` SKILL.md (read
  from disk) + the transcript + the previous `error` if any.
- Strip accidental ``` fences before validating.
- Save every raw response to `run_dir/director_attempt_<n>.txt` for debugging.
- Never use the `anthropic` SDK or an API key.

## Silent scenes

`narrate` only calls TTS for scenes with `narration`. Every scene's duration is
max(narration + pad, the action's move timeline, `min_scene_s`); silent scenes get
a silent WAV of that length, so `render` and `compose` need no special cases.

## Validation

`VideoPlan.model_validate_json(raw)`. On `ValidationError`, store `str(e)` in
`error`. Also check things Pydantic can't express easily (figures 0.3 apart,
total narration 25–45 words, the rules of each `audio_mode`) with a
`@model_validator`. Action scenes are checked by `render/choreo.check_scene`,
which simulates the moves; its messages say exactly what to change, because they
go straight back to the director.

## Running and debugging

- `python -m shorts.run input/example.txt` — full run.
- `python -m shorts.run input/example.txt --plan tests/fixtures/plan_example.json`
  — skip Claude.
- `app.get_graph().draw_mermaid()` — print the graph; check it after edge changes.
- Use `app.stream(state, stream_mode="updates")` in `run.py` to print which node
  ran and what it changed. That's the main debugging view.

## Tests

- One test per node in `tests/`, using the fixture plan. Tests must not call Claude:
  monkeypatch `shorts.llm.call_claude` to return fixture JSON.
- One end-to-end test with `--plan` that checks the MP4 exists and lasts 10–20 s.
