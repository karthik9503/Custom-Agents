"""narrate: one WAV per scene, and each scene's duration.

Narrated scenes: TTS, and the duration comes from the audio length.
Silent action scenes: no TTS; the duration comes from the move timeline, and the
WAV is silence of that length (so compose treats every scene the same way).
"""

from pathlib import Path

import numpy as np
import soundfile as sf

from shorts import tts  # module import so tests can monkeypatch tts.synthesize
from shorts.render.choreo import scene_length
from shorts.state import ShortState
from shorts.style import load_style

SILENCE_RATE = 22050


def scene_durations(audio_lengths: list[float], timing: dict, action_lengths: list[float] | None = None) -> list[float]:
    """Scene length = narration + pad (or the action's length, if longer), at least min_scene_s.

    If the whole video is shorter than min_total_s, the last scene is held
    longer. We never cut or speed up narration, so long plans just warn.
    """
    action_lengths = action_lengths or [0.0] * len(audio_lengths)
    durations = []
    for audio, action in zip(audio_lengths, action_lengths):
        spoken = audio + timing["pad_after_narration_s"] if audio > 0 else 0.0
        durations.append(max(timing["min_scene_s"], spoken, action))
    total = sum(durations)
    if total < timing["min_total_s"]:
        durations[-1] += timing["min_total_s"] - total
    for i, (d, action) in enumerate(zip(durations, action_lengths)):
        if d > timing["max_scene_s"] and not action:  # action scenes may run longer
            print(f"  warning: scene {i} is {d:.1f}s (max {timing['max_scene_s']}s)")
    if sum(durations) > timing["max_total_s"]:
        print(f"  warning: video is {sum(durations):.1f}s (max {timing['max_total_s']}s)")
    return durations


def narrate(state: ShortState) -> dict:
    audio_dir = Path(state["run_dir"], "audio")
    audio_dir.mkdir(parents=True, exist_ok=True)
    style = load_style()
    scenes = state["plan"]["scenes"]

    lengths, action_lengths = [], []
    for i, scene in enumerate(scenes):
        action_lengths.append(scene_length(scene, style))
        if scene.get("narration"):
            path = audio_dir / f"scene_{i:02d}.wav"
            engine = tts.synthesize(scene["narration"], path)
            length = sf.info(str(path)).duration
            print(f"  scene {i}: {length:.2f}s ({engine})")
        else:
            length = 0.0
            print(f"  scene {i}: silent, action {action_lengths[-1]:.2f}s")
        lengths.append(length)

    durations = scene_durations(lengths, style["timing"], action_lengths)

    # Silent scenes get a silent track as long as the scene itself.
    paths = []
    for i, (scene, duration) in enumerate(zip(scenes, durations)):
        path = audio_dir / f"scene_{i:02d}.wav"
        if not scene.get("narration"):
            sf.write(str(path), np.zeros(int(SILENCE_RATE * duration), dtype="float32"), SILENCE_RATE)
        paths.append(str(path))
    return {"audio_paths": paths, "durations": durations}
