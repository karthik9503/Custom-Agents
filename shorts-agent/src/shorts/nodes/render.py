"""render: draw each scene's frames into a silent clip."""

from pathlib import Path

from moviepy import VideoClip

from shorts.render.scene import SceneRenderer, draw_safe_zone
from shorts.state import ShortState
from shorts.style import load_style


def render(state: ShortState) -> dict:
    style = load_style()
    fps = style["canvas"]["fps"]
    clips_dir = Path(state["run_dir"], "clips")
    clips_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i, (scene, duration) in enumerate(zip(state["plan"]["scenes"], state["durations"])):
        renderer = SceneRenderer(scene, duration, style)
        if state.get("debug"):
            _save_debug_frame(renderer, style, Path(state["run_dir"], "debug", f"scene_{i:02d}.png"))

        # Frames are generated on demand: holding 150 full-HD frames in memory
        # per scene (ImageSequenceClip) would take ~1 GB.
        clip = VideoClip(renderer.frame_at, duration=duration)
        path = clips_dir / f"scene_{i:02d}.mp4"
        clip.write_videofile(
            str(path), fps=fps, codec="libx264", audio=False, preset="veryfast",
            # Near-lossless intermediates; compose does the final encode.
            ffmpeg_params=["-crf", "16", "-pix_fmt", "yuv420p"], logger=None,
        )
        clip.close()
        print(f"  scene {i}: {renderer.n_frames} frames")
        paths.append(str(path))
    return {"clip_paths": paths}


def _save_debug_frame(renderer: SceneRenderer, style: dict, path: Path) -> None:
    # The last frame: every action (slide-in, pop, count-up) has finished by then.
    img = renderer.frame(renderer.n_frames - 1)
    draw_safe_zone(img, style)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
