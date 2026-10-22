# Build plan — prompts to paste into Claude Code (VS Code)

Do ONE step per message. Run and test it yourself before moving to the next.
After each step, commit: `git add . && git commit -m "step N"` (if you installed Git).

---

### Step 0 — Orientation
> Read CLAUDE.md and all the docs it links. Summarise the project in 5 bullet points and
> explain the agent loop in your own words. Don't write any code yet.

### Step 1 — Talk to the model (llm.py)
> Build step 1: create `src/llm.py` with one function
> `ask_model(system: str, transcript: str) -> str`
> that runs `claude -p` exactly as described in ARCHITECTURE.md (stdin, --output-format json,
> --tools "", cwd=.runtime) and returns `data["result"]`. Handle timeout and non-zero exit
> with a clear error. Add a tiny `if __name__ == "__main__"` test that asks "say hello".
> Explain each flag.

### Step 2 — Chat loop with no tools (main.py)
> Build step 2: `src/main.py`, a loop that reads my input, sends it to `ask_model`, and prints
> the reply. Typing `exit` quits. No tools yet. Explain why this is a chatbot, not an agent.

### Step 3 — First tool + the parser
> Build step 3: in `src/tools.py` add `list_notes` and `read_note` with the safety checks
> from SECURITY.md, plus a `TOOLS` dict and `TOOL_SCHEMAS` (API format, see ARCHITECTURE.md).
> Add `render_tools(schemas)` and `build_system_prompt()` that fills `{{TOOLS}}` in
> prompts/system.md. In `src/agent.py` add `parse_reply(text)` that
> returns either a tool call or a final answer (handle ```json fences and invalid JSON).
> Add tests in `tests/test_tools.py` and `tests/test_parse.py`. Don't build the loop yet.

### Step 4 — The agent loop ⭐ (the most important step)
> Build step 4: `run_agent(user_message, history)` in `src/agent.py`, following ARCHITECTURE.md:
> transcript → model → parse → run tool → add TOOL RESULT → repeat until "final", max 10
> tool calls, retry on invalid JSON. Print each tool call and result. Wire it into main.py.
> Let me try writing the loop first — give me hints, then review my version.

### Step 5 — Remaining tools
> Build step 5: add `write_note`, `append_note`, `search_notes`, `delete_note` (with terminal
> confirmation). Tests for each.

### Step 6 — Guardrails and errors
> Build step 6: check every rule in SECURITY.md is implemented. Add result truncation and
> size limits. Show me how the agent recovers when I ask to read a note that doesn't exist.

### Step 7 — Test the loop with a fake model
> Build step 7: `tests/test_agent.py` that tests run_agent with a fake ask_model function
> (pre-written replies), including the max-10 limit and the invalid-JSON retry.

### Step 8 — Scenario testing
> Copy examples/notes into notes/. Walk me through running every request in the PRD table,
> and help me write the results into examples/transcripts.md.

### Step 9 (bonus) — Same tools as an MCP server
> Explain MCP, then help me turn tools.py into a small MCP server and connect it to Claude
> Code, so I can compare my agent with a professional one using the same tools.
