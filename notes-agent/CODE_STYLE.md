# Code style

- Python 3.10+, **standard library only** (`subprocess`, `json`, `pathlib`, `datetime`, `unittest`).
- Small functions with clear names. Type hints on every function.
- Docstrings: one line saying what the function does.
- Use `pathlib.Path` for all paths; read/write files with `encoding="utf-8"`.
- Tool functions **always return a string** (even on error) and never raise to the agent loop.
  Error strings start with `ERROR:` so the model can recognise them.
- No global mutable state except the `TOOLS` registry in `tools.py`.
- Comments explain *why*, not *what*.
- Format with 4-space indents, max ~100 chars per line.
