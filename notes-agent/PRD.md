# PRD — Notes Assistant

## Goal
A terminal chat agent that manages a folder of Markdown notes. The user types requests in
plain English; the agent decides which tools to call, calls them (possibly several in a row),
and replies with a short answer.

## Why (learning goals)
Learn the core parts of an agent by building them by hand:
the agent loop, tool definitions, tool-call parsing, error recovery, guardrails, and testing.

## Users
One user (the developer), on their own laptop.

## Example requests it must handle
| Request | Expected tool calls |
|---|---|
| "What notes do I have?" | `list_notes` |
| "Save a note called groceries: milk, eggs, rice" | `write_note` |
| "Add 'buy bread' to groceries" | `read_note` → `append_note` |
| "What did I write about Python?" | `search_notes` → `read_note` |
| "Summarize all my notes" | `list_notes` → `read_note` (each) |
| "Delete the groceries note" | `delete_note` (asks user to type yes first) |
| "Read my diary note" (doesn't exist) | `read_note` → error → tells the user it doesn't exist |

## Tools (v1)
| Tool | Args | Returns |
|---|---|---|
| `list_notes` | — | note names + last-modified date |
| `read_note` | `name` | the note's text |
| `write_note` | `name`, `content` | confirmation (creates or replaces) |
| `append_note` | `name`, `text` | confirmation |
| `search_notes` | `keyword` | matching note names + matching lines |
| `delete_note` | `name` | confirmation, only after the user types `yes` |

## Non-goals (v1)
No GUI, no web search, no database, no multiple users, no paid APIs.

## Later ideas (v2+)
Conversation memory across runs, tags, MCP server version of the tools (plug into Claude Code),
summarising long history.
