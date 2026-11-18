"""The LangGraph state. Each field notes the node that writes it."""

from typing import TypedDict


class ShortState(TypedDict, total=False):
    run_id: str              # run.py
    run_dir: str             # run.py: output/<run_id>
    transcript: str          # run.py
    plan_file: str | None    # run.py: set when started with --plan (skip Claude)
    debug: bool              # run.py: save debug frames
    raw_plan: str            # director (or run.py with --plan)
    plan: dict | None        # validate: VideoPlan.model_dump()
    error: str | None        # validate: last validation error
    attempts: int            # director: attempts so far
    audio_paths: list[str]   # narrate
    durations: list[float]   # narrate: seconds per scene (narration + pad)
    clip_paths: list[str]    # render
    video_path: str          # compose
