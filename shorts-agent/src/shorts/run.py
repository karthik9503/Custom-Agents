"""CLI: python -m shorts.run input/x.txt [--plan p.json] [--debug] [--graph]"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from shorts.graph import build_graph
from shorts.state import ShortState
from shorts.style import ROOT


def make_run_id(input_path: Path) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", input_path.stem.lower()).strip("-") or "run"
    return f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"


def summarize(value) -> str:
    """Short, readable view of a state value for the progress log."""
    if isinstance(value, list):
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        return "{" + ", ".join(value) + "}"
    text = str(value).replace("\n", " ")
    return text if len(text) <= 70 else text[:67] + "..."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn a transcript into a stick-figure short.")
    parser.add_argument("transcript", type=Path, help="path to a .txt transcript")
    parser.add_argument("--plan", type=Path, help="use this VideoPlan JSON instead of calling Claude")
    parser.add_argument("--debug", action="store_true", help="save a frame of every scene to debug/")
    parser.add_argument("--graph", action="store_true", help="print the graph as Mermaid and exit")
    args = parser.parse_args(argv)

    app = build_graph()
    if args.graph:
        print(app.get_graph().draw_mermaid())
        return 0

    run_id = make_run_id(args.transcript)
    run_dir = ROOT / "output" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    state: ShortState = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "transcript": args.transcript.read_text(encoding="utf-8"),
        "plan_file": str(args.plan) if args.plan else None,
        "debug": args.debug,
        "attempts": 0,
    }
    if args.plan:
        state["raw_plan"] = args.plan.read_text(encoding="utf-8")

    print(f"run {run_id}")
    final = dict(state)
    # stream_mode="updates" yields {node_name: fields_it_changed} after each node.
    for update in app.stream(state, stream_mode="updates"):
        for node, changes in update.items():
            print(f"[{node}] " + ", ".join(f"{k}={summarize(v)}" for k, v in (changes or {}).items()))
            final.update(changes or {})

    if final.get("video_path"):
        print(f"\ndone: {final['video_path']}")
        return 0
    print(f"\nfailed after {final.get('attempts', 0)} director attempt(s). Last error:\n{final.get('error')}")
    print(f"raw responses are in {run_dir}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
