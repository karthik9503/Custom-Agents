"""compose: join scene clips + narration (+ optional music) into short.mp4."""

from pathlib import Path

from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip, afx, concatenate_videoclips

from shorts.state import ShortState
from shorts.style import load_style, project_path


def compose(state: ShortState) -> dict:
    style = load_style()
    run_dir = Path(state["run_dir"])
    out = run_dir / "short.mp4"

    opened = []  # everything to close afterwards (Windows locks open files)
    clips = []
    for clip_path, audio_path in zip(state["clip_paths"], state["audio_paths"]):
        video = VideoFileClip(clip_path)
        audio = AudioFileClip(audio_path)
        opened += [video, audio]
        # Trim so a scene's audio can never spill into the next scene.
        audio = audio.subclipped(0, min(audio.duration, video.duration))
        clips.append(video.with_audio(audio))

    final = concatenate_videoclips(clips, method="chain")  # hard cuts only

    music_cfg = style.get("music") or {}
    if music_cfg.get("path"):
        music_path = project_path(music_cfg["path"])
        if music_path.exists():
            music = AudioFileClip(str(music_path))
            opened.append(music)
            music = music.subclipped(0, min(music.duration, final.duration)).with_effects([
                afx.MultiplyVolume(music_cfg["volume"]),
                afx.AudioFadeOut(music_cfg["fade_out_s"]),
            ])
            final = final.with_audio(CompositeAudioClip([final.audio, music]))
        else:
            print(f"  music not found, skipping: {music_path}")

    final.write_videofile(
        str(out), fps=style["canvas"]["fps"], codec="libx264", audio_codec="aac",
        ffmpeg_params=["-pix_fmt", "yuv420p"],  # plays on phones
        temp_audiofile=str(run_dir / "temp_audio.m4a"),  # keep temp files in run_dir
        logger=None,
    )
    print(f"  {final.duration:.1f}s -> {out}")
    final.close()
    for clip in opened:
        clip.close()
    return {"video_path": str(out)}
