# Architecture

## Big picture

```
 you type ──► main.py (chat loop)
                 │
                 ▼
             agent.py (agent loop) ◄──────────────┐
                 │  sends whole transcript        │ tool result
                 ▼                                │
             llm.py ── subprocess ──► claude -p   │
                 │  reply (JSON text)             │
                 ▼                                │
             parse reply:                         │
               {"tool": ..., "args": {...}} ──► tools.py ─┘
               {"final": "..."}           ──► print answer, wait for next message
```

## Files

```
notes-agent/
  src/
    main.py      # terminal chat loop: read input, call agent, print answer
    agent.py     # the agent loop: model → tool → model ... → final
    llm.py       # the ONLY place that runs `claude -p`
    tools.py     # the 6 tool functions, TOOL_SCHEMAS (API format) + a TOOLS registry dict
  prompts/
    system.md    # the agent's instructions: job, reply format, rules; {{TOOLS}} is filled in
                 # from TOOL_SCHEMAS at runtime
  notes/         # the user's notes (*.md). The agent may only touch files here.
  tests/         # unittest tests
  examples/      # sample notes + example transcripts
  .runtime/      # empty folder used as the working dir for `claude -p`
```

## Tool schemas (one source of truth)

Each tool is described once in `tools.py`, in the exact format the Anthropic API uses:

```python
TOOL_SCHEMAS = [
    {
        "name": "append_note",
        "description": "Add text to the end of an existing note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Note name, e.g. groceries"},
                "text": {"type": "string", "description": "Text to add"},
            },
            "required": ["name", "text"],
        },
    },
    # ...one entry per tool
]
```

- **CLI backend (now):** `render_tools(TOOL_SCHEMAS)` turns this into text lines like
  `- append_note(name, text) -> Add text to the end of an existing note.` and replaces
  `{{TOOLS}}` in `prompts/system.md`.
- **Arg checking:** before running a tool, the agent loop checks the args against
  `input_schema` (required keys present, values are strings) and returns `ERROR:` if not.
- **API backend (later):** the same list is sent unchanged as `tools=`.

## The model call (llm.py)

`ask_model(system: str, transcript: str) -> str` — the system prompt is built in code (with the
tools filled in), so it is passed as a string. The full conversation is sent through **stdin**
(not as an argument) so quotes, new lines and long text are safe:

```python
cmd = [
    "claude", "-p",
    "--safe-mode",                                # no CLAUDE.md, skills, hooks or MCP
    "--system-prompt", system,                    # replace Claude Code's default prompt
    "--output-format", "json",                    # reply text is in data["result"]
    "--no-session-persistence",                   # each call is stateless, like an API
    "--model", "haiku",                           # fast and small is enough
    "--tools", "",                                # NO built-in tools: we do tool calling ourselves
]
subprocess.run(cmd, input=transcript, capture_output=True, text=True,
               encoding="utf-8", timeout=120, cwd=RUNTIME_DIR)
```

- `--safe-mode` stops the agent's `claude -p` from loading this repo's CLAUDE.md, which is
  meant for Claude Code, not for the Notes Assistant. Running in `.runtime/` alone is NOT
  enough: Claude Code also searches parent folders for CLAUDE.md. `--safe-mode` keeps the
  Pro login working.
- `cwd=RUNTIME_DIR` (an empty `.runtime/` folder) is just a scratch folder outside `src/`.
- Do NOT add `--bare`: it does not use the Pro login.
- Each call takes a few seconds. That's expected.

## Reply protocol (we build "tool calling" by hand)

The model must reply with exactly ONE JSON object and nothing else:

```json
{"tool": "read_note", "args": {"name": "groceries"}}
```
or
```json
{"final": "Done — groceries now has 4 items."}
```

## Transcript format

The agent keeps a list of messages and turns it into plain text for each call:

```
USER: add buy bread to groceries
ASSISTANT: {"tool": "read_note", "args": {"name": "groceries"}}
TOOL RESULT (read_note): milk, eggs, rice
ASSISTANT: {"tool": "append_note", "args": {"name": "groceries", "text": "buy bread"}}
TOOL RESULT (append_note): ok, appended to groceries
```

## Agent loop rules
- Max **10** tool calls per user request, then stop and tell the user.
- If the reply isn't valid JSON: add `TOOL RESULT (error): reply was not valid JSON, reply with
  one JSON object only` and retry. Max 2 retries.
- Unknown tool or bad args → return an error string to the model, don't crash.
- Print every tool call and result to the terminal (dim/grey) so the user can watch it think.

## Future: API backend

The plan is to swap `claude -p` for direct Anthropic API calls later. To keep that swap small:
- The agent loop only works with normalized replies from `parse_reply`:
  `{"tool": name, "args": {...}}` or `{"final": text}` — never with raw backend output.
- Only these change in the swap: `llm.py` (or a new `llm_api.py` using `urllib`), the reply
  parser (API returns `tool_use` blocks instead of JSON text), and the transcript (API takes a
  list of messages instead of one text block).
- `tools.py`, `TOOL_SCHEMAS`, the guardrails and the loop rules stay the same.
