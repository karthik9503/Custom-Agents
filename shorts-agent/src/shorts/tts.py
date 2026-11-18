"""Offline text-to-speech: Piper first, pyttsx3 as a fallback."""

import wave
from functools import lru_cache
from pathlib import Path

from shorts.style import load_style, project_path


@lru_cache(maxsize=1)
def _piper_voice(model_path: str):
    from piper import PiperVoice  # imported lazily: heavy, and optional in tests

    return PiperVoice.load(model_path)


def _synthesize_piper(text: str, out_path: Path, model: Path) -> None:
    if not model.exists():
        raise FileNotFoundError(f"Piper voice not found: {model}")
    voice = _piper_voice(str(model))
    with wave.open(str(out_path), "wb") as wav_file:
        # piper-tts >= 1.3 renamed the WAV writer to synthesize_wav().
        if hasattr(voice, "synthesize_wav"):
            voice.synthesize_wav(text, wav_file)
        else:
            voice.synthesize(text, wav_file)


def _synthesize_pyttsx3(text: str, out_path: Path) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.save_to_file(text, str(out_path))
    engine.runAndWait()
    engine.stop()


def synthesize(text: str, out_path: Path) -> str:
    """Write `text` as speech to `out_path` (WAV). Returns the engine that was used."""
    voice = load_style()["voice"]
    if voice["engine"] == "piper":
        try:
            _synthesize_piper(text, out_path, project_path(voice["piper_model"]))
            return "piper"
        except Exception as e:  # missing model, import error, ...
            if voice.get("fallback") != "pyttsx3":
                raise
            print(f"  piper failed ({e}); falling back to pyttsx3")
    _synthesize_pyttsx3(text, out_path)
    return "pyttsx3"
