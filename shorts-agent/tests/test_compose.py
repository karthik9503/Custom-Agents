from moviepy import VideoFileClip

from shorts.nodes.compose import compose
from shorts.nodes.narrate import narrate
from shorts.nodes.render import render


def test_compose_joins_clips(fake_tts, plan, run_dir):
    state = {"plan": plan, "run_dir": run_dir}
    state |= narrate(state)
    state["durations"] = [1.0] * len(plan["scenes"])  # shorter than narration is fine here
    state |= render(state)
    out = compose(state)
    with VideoFileClip(out["video_path"]) as clip:
        assert abs(clip.duration - 4.0) < 0.2
        assert clip.audio is not None
