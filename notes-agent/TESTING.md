# Testing

## 1. Unit tests (fast, no model calls)
`python -m unittest discover tests`

- `tests/test_tools.py` — each tool works on a temporary notes folder; path escape
  (`../secret`) is rejected; missing note returns an `ERROR:` string.
- `tests/test_parse.py` — reply parsing: valid tool call, valid final, JSON wrapped in
  ```json fences, plain text (invalid), unknown tool.
- `tests/test_agent.py` — the agent loop with a **fake LLM** (a function that returns
  pre-written replies), so the loop logic is tested without calling Claude.

## 2. Scenario tests (manual, uses real model calls)
Copy `examples/notes/*` into `notes/`, then run `python src/main.py` and try each
request from the table in PRD.md. For each, check:
- the right tools were called, in a sensible order
- the final answer is correct and short
- nothing outside `notes/` was touched

Keep a log in `examples/transcripts.md` of what happened. Re-run these after every change to
`prompts/system.md` or the tools — prompt changes can break things that used to work.
