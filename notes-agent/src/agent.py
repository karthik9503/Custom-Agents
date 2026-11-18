"""The agent: builds its system prompt and understands the model's replies."""

import json
from pathlib import Path

from tools import TOOL_SCHEMAS, TOOLS

SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "system.md"


def render_tools(schemas: list[dict]) -> str:
    """Turn API-style tool schemas into the plain-text tool list the CLI model reads."""
    lines = []
    for schema in schemas:
        properties = schema["input_schema"]["properties"]
        lines.append(f"- {schema['name']}({', '.join(properties)}) -> {schema['description']}")
        for arg, details in properties.items():
            lines.append(f"    {arg}: {details['description']}")
    return "\n".join(lines)


def build_system_prompt() -> str:
    """Read prompts/system.md and fill in the tool list."""
    template = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    return template.replace("{{TOOLS}}", render_tools(TOOL_SCHEMAS))


def parse_reply(text: str) -> dict:
    """Turn the model's reply into {"tool", "args"}, {"final"} or {"error"}."""
    text = text.strip()
    # Models often wrap JSON in ```json fences even when told not to.
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].removesuffix("```").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Second chance: the JSON may be surrounded by a sentence of chatter.
        try:
            data = json.loads(text[text.find("{"):text.rfind("}") + 1])
        except json.JSONDecodeError:
            return {"error": "reply was not valid JSON, reply with one JSON object only"}

    if not isinstance(data, dict):
        return {"error": "reply must be one JSON object"}
    if isinstance(data.get("final"), str):
        return {"final": data["final"]}
    if "tool" in data:
        name, args = data["tool"], data.get("args", {})
        if name not in TOOLS:
            return {"error": f"unknown tool '{name}'. Available tools: {', '.join(TOOLS)}"}
        if not isinstance(args, dict):
            return {"error": "'args' must be a JSON object"}
        return {"tool": name, "args": args}
    return {"error": 'reply must contain "tool" or "final"'}


if __name__ == "__main__":
    # See exactly what the model will be told: `python src/agent.py`
    print(build_system_prompt())
