# AGENTS.md — how Claude Code should work in this repo

There are two different "agents" in this project. Don't mix them up:

1. **Claude Code (you)** — the coding assistant helping build this project.
2. **The Notes Assistant** — the agent we are building. It is a Python program in `src/`
   that calls `claude -p` as its "brain".

## Teaching mode (always on)

- Build **one step at a time**, following the step order in `BUILD_PLAN.md`.
  Never jump ahead or build several steps at once.
- Before writing code, explain in 3–5 plain sentences **what** you will build and **why**.
- Keep each change small (ideally under ~80 lines). Prefer simple code over clever code.
- After writing code, explain the key lines and tell me exactly how to run and test it.
- End every step with 1–2 questions that check I understood (e.g. "What happens if the
  model replies with text that isn't JSON?").
- If I ask you to "let me try first", give hints only, not the full solution.
- Never add a framework or library (LangChain, Anthropic SDK, etc.). Standard library only.
- Build with a future switch from `claude -p` to direct API calls in mind (see "Future: API
  backend" in ARCHITECTURE.md). When that happens, call the API with `urllib`, not the SDK,
  unless I change this rule.

## Commands

- Run the agent: `python src/main.py`
- Run tests: `python -m unittest discover tests`
- OS: Windows 11, PowerShell. Python from Anaconda. Use Windows-friendly paths
  (`pathlib.Path`), never hard-coded `/` paths.

## Do not

- Do not edit files in `notes/` directly while testing — let the agent do it.
- Do not change `prompts/system.md` without explaining why; it is the agent's behaviour.
- Do not use `--bare` with `claude -p`: bare mode ignores the Pro subscription login.
