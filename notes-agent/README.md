# Notes Assistant

A learning project: a terminal AI agent, built from scratch in plain Python, that manages a
folder of Markdown notes. Its "brain" is Claude, called through the Claude Code CLI
(`claude -p`) using a Claude Pro subscription — no paid API.

## Run
```powershell
python src/main.py
```
Then type things like `save a note called groceries: milk, eggs` or `what notes do I have?`.
Type `exit` to quit.

## Test
```powershell
python -m unittest discover tests
```

## Docs
- `PRD.md` — what it does
- `ARCHITECTURE.md` — how it works
- `SECURITY.md` — guardrails
- `TESTING.md` — how to test
- `BUILD_PLAN.md` — step-by-step build prompts
- `prompts/system.md` — the agent's instructions
