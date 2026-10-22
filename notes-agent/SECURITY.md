# Security and guardrails

An agent takes actions, so it needs limits. These are required, not optional.

1. **Sandbox to `notes/`.** Every tool resolves the path and checks it is inside `notes/`.
   Reject names containing `/`, `\`, `..` or a drive letter. Only `.md` files.
2. **Name rules.** Note names: letters, numbers, `-`, `_`, spaces; max 50 chars.
3. **Confirm destructive actions.** `delete_note` asks the human in the terminal
   (`Type yes to delete 'x':`). The model can never confirm on the user's behalf.
   `write_note` on an existing note should say it replaced the old content.
4. **Size limits.** Truncate tool results over ~4,000 characters (`...[truncated]`) and refuse
   to write notes over 50 KB.
5. **Loop limit.** Max 10 tool calls per request so a confused model can't run forever.
6. **Notes are data, not instructions.** The system prompt tells the model to ignore any
   instructions written inside notes.
7. **No shell, no network.** The agent's tools never run shell commands or open URLs.
   `claude -p` is called with `--tools ""` so Claude Code's own tools are off.
