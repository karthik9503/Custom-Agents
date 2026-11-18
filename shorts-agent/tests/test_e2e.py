from pathlib import Path

from moviepy import VideoFileClip

from shorts import run

ROOT = Path(__file__).resolve().parents[1]


def test_full_run_with_plan(fake_tts, monkeypatch, tmp_path):
    def no_claude(*_args, **_kwargs):
        raise AssertionError("--plan must not call Claude")

    monkeypatch.setattr("shorts.llm.call_claude", no_claude)
    monkeypatch.setattr(run, "ROOT", tmp_path)  # write output/ into the temp dir

    code = run.main([str(ROOT / "input" / "example.txt"),
                     "--plan", str(ROOT / "tests" / "fixtures" / "plan_example.json")])
    assert code == 0

    [video] = tmp_path.glob("output/*/short.mp4")
    with VideoFileClip(str(video)) as clip:
        assert 10 <= clip.duration <= 20
        assert clip.size == [1080, 1920]
