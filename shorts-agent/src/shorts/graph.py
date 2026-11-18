"""Builds the LangGraph. All flow lives here; nodes never call each other."""

from langgraph.graph import END, START, StateGraph

from shorts.nodes.compose import compose
from shorts.nodes.director import director
from shorts.nodes.narrate import narrate
from shorts.nodes.render import render
from shorts.nodes.validate import validate
from shorts.state import ShortState

MAX_ATTEMPTS = 3


def start_router(state: ShortState) -> str:
    # With --plan, run.py already put the plan in raw_plan: skip Claude.
    return "validate" if state.get("raw_plan") else "director"


def after_validate(state: ShortState) -> str:
    if not state.get("error"):
        return "narrate"
    if state.get("plan_file"):
        return END  # a bad --plan file won't fix itself; don't call Claude
    if state.get("attempts", 0) < MAX_ATTEMPTS:
        return "director"
    return END


def build_graph():
    g = StateGraph(ShortState)
    g.add_node("director", director)
    g.add_node("validate", validate)
    g.add_node("narrate", narrate)
    g.add_node("render", render)
    g.add_node("compose", compose)

    # The lists name every possible target, so draw_mermaid() shows all edges.
    g.add_conditional_edges(START, start_router, ["director", "validate"])
    g.add_edge("director", "validate")
    g.add_conditional_edges("validate", after_validate, ["narrate", "director", END])
    g.add_edge("narrate", "render")
    g.add_edge("render", "compose")
    g.add_edge("compose", END)
    return g.compile()
