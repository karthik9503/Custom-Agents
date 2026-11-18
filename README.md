# Custom Agents

Small agents built while learning agent development with Claude Code. Each folder is a
self-contained project with its own README, setup and tests.

| Agent | What it does |
|---|---|
| [notes-agent](notes-agent/) | A notes assistant that reads and writes markdown notes through tools, using `claude -p` as the model |
| [shorts-agent](shorts-agent/) | A LangGraph pipeline that turns a transcript into a 10–20 s vertical stick-figure video with offline narration |

Both agents call Claude only through Claude Code's headless mode (`claude -p`); no paid APIs.
