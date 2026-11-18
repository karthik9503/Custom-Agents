"""The only door to an LLM: Claude Code in headless mode (`claude -p`).

No `anthropic` SDK and no API key. This uses the user's logged-in Claude plan.
"""

import json
import os
import shutil
import subprocess
import tempfile


class ClaudeError(RuntimeError):
    pass


def call_claude(prompt: str, timeout: int = 180) -> str:
    """Send `prompt` to `claude -p --output-format json` and return the `result` text."""
    # On Windows `claude` is a .cmd shim, which subprocess can't find by bare name.
    exe = shutil.which("claude")
    if exe is None:
        raise ClaudeError("`claude` CLI not found on PATH. Install Claude Code and run `claude login`.")

    env = os.environ.copy()
    # Never bill an API key: force the logged-in plan.
    env.pop("ANTHROPIC_API_KEY", None)
    # Allow running the pipeline from inside a Claude Code terminal.
    env.pop("CLAUDECODE", None)

    try:
        out = subprocess.run(
            [exe, "-p", "--output-format", "json"],
            # The prompt goes in on stdin: long multi-line prompts break
            # command-line quoting on Windows .cmd shims.
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=True,
            # Run outside the project so this repo's CLAUDE.md (dev instructions)
            # doesn't leak into the director's context.
            cwd=tempfile.gettempdir(),
            env=env,
        )
    except subprocess.CalledProcessError as e:
        raise ClaudeError(f"claude exited with {e.returncode}: {e.stderr or e.stdout}") from e
    except subprocess.TimeoutExpired as e:
        raise ClaudeError(f"claude timed out after {timeout}s") from e

    data = json.loads(out.stdout)
    if data.get("is_error"):
        raise ClaudeError(f"claude reported an error: {data.get('result')}")
    return data["result"]
