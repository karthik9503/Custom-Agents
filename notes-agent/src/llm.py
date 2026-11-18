"""Talk to the model. This is the ONLY file that runs `claude -p`."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# An empty scratch folder to run `claude -p` in, so it never works inside the repo itself.
RUNTIME_DIR = ROOT / ".runtime"
TIMEOUT_SECONDS = 120


def ask_model(system: str, transcript: str) -> str:
    """Send the system prompt and transcript to Claude and return its reply text."""
    # Look the CLI up on PATH ourselves, so a missing install gives a clear message.
    claude = shutil.which("claude")
    if claude is None:
        raise RuntimeError("Could not find the `claude` CLI. Is Claude Code installed?")

    cmd = [
        claude, "-p",                  # print mode: answer once and exit, no chat UI
        # Skip CLAUDE.md, skills, hooks and MCP. Claude Code searches parent folders for
        # CLAUDE.md, so running in .runtime/ alone still loaded this repo's file.
        "--safe-mode",
        "--system-prompt", system,     # replace Claude Code's own prompt with ours
        "--output-format", "json",     # wrap the reply in JSON so we can read it reliably
        "--no-session-persistence",    # stateless, like an API: we send the full history
        "--model", "haiku",            # small and fast is enough for picking tools
        "--tools", "",                 # no built-in tools: OUR program runs the tools
    ]
    try:
        # The transcript goes through stdin, so quotes and new lines are safe.
        result = subprocess.run(cmd, input=transcript, capture_output=True, text=True,
                                encoding="utf-8", timeout=TIMEOUT_SECONDS, cwd=RUNTIME_DIR)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"The model did not answer within {TIMEOUT_SECONDS} seconds.")

    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"claude -p failed (exit code {result.returncode}): {details}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude -p did not return JSON: {result.stdout[:200]}")

    if data.get("is_error"):
        raise RuntimeError(f"claude -p reported an error: {data.get('result')}")
    return data["result"]


if __name__ == "__main__":
    # Quick manual check: `python src/llm.py`
    print(ask_model("You are a friendly assistant. Reply in one short sentence.",
                    "USER: say hello"))
