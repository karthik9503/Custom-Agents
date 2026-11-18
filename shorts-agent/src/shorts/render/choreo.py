"""Choreography: turns an "action" scene from the plan into Actors, and checks it.

The checks simulate the scene with the same Tracks the renderer draws, so "the
punch reaches" means it really reaches on screen. Every error message says what
to change, because it goes straight back to the director for a retry.
"""

from shorts.render.action import ActionScene, Actor, action_height
from shorts.render.moves import MOVES, REACTIONS, Step, Track
from shorts.style import load_style

RGB = tuple[int, int, int]
_BLACK = (0, 0, 0)

# Roughly how far apart (in figure heights) fighters stand for each strike to land.
REACH = {"punch": 0.55, "kick": 0.55, "slash": 0.85}
# How long after a strike starts it lands (seconds); listed in the director skill.
LANDS_AFTER = {name: next(k.t for k in MOVES[name].keys if k.impact) for name in REACH}
_FALLS_SHORT_TOLERANCE = 0.25  # figure heights
_MIN_GAP = 0.35                # figure heights between two fighters' centers


def build_actors(scene: dict, style: dict, ink: RGB = _BLACK, accent: RGB = _BLACK) -> list[Actor]:
    w = style["canvas"]["width"]
    height = action_height(style)
    actors = []
    for c in scene["characters"]:
        steps = [Step(m["move"], at=m["at"], to_x=None if m.get("to_x") is None else m["to_x"] * w)
                 for m in c.get("moves", [])]
        track = Track(x=c["x"] * w, facing=c["facing"], height=height, steps=steps, pose=c["pose"])
        actors.append(Actor(track, accent if c.get("color") == "accent" else ink, c.get("holds")))
    return actors


def action_scene(scene: dict, style: dict, ink: RGB = _BLACK, accent: RGB = _BLACK,
                 bg: RGB = (255, 255, 255)) -> ActionScene:
    ground = int(style["canvas"]["height"] * style["figure"]["ground_y"])
    return ActionScene(build_actors(scene, style, ink, accent), ground, style, bg, accent)


def scene_length(scene: dict, style: dict | None = None) -> float:
    """Seconds an action scene needs: its last move, plus a short hold. 0 for other layouts."""
    if scene["layout"] != "action":
        return 0.0
    style = style or load_style()
    actors = build_actors(scene, style)
    return max(a.track.end_time for a in actors) + style["action"]["hold_s"]


def _move_at(track: Track, t: float) -> str:
    """Name of the move that is playing at time t."""
    name = track.events[0][1] if track.events else "stance"
    for start, move in track.events:
        if start <= t:
            name = move
    return name


def check_scene(scene: dict, style: dict | None = None) -> list[str]:
    """Problems with an action scene's choreography (empty list = fine)."""
    style = style or load_style()
    w = style["canvas"]["width"]
    sim = action_scene(scene, style)
    ids = [c["id"] for c in scene["characters"]]
    fighters = list(zip(ids, scene["characters"], sim.actors))
    height = sim.actors[0].track.height
    errors: list[str] = []

    # 1. Each character's moves happen one after another.
    for cid, c, actor in fighters:
        for m, (start, _) in zip(c.get("moves", []), actor.track.events):
            if start > m["at"] + 1e-6:
                errors.append(f"{cid}'s {m['move']!r} at {m['at']} s starts before their previous move "
                              f"ends ({start:.2f} s); start it at {start:.2f} s or later")

    # 2. Everyone stays on screen.
    for cid, _, actor in fighters:
        xs = [k.x for k in actor.track.keys]
        if min(xs) < 0 or max(xs) > w:
            errors.append(f"{cid} goes off-screen (x {min(xs) / w:.2f}..{max(xs) / w:.2f}); "
                          "keep everyone between x 0.05 and 0.95, e.g. start further from the edge")

    # 3. Strikes and reactions line up, and strikes reach.
    if len(fighters) >= 2:
        impacts = []
        for cid, _, attacker in fighters:
            for t, joint in attacker.track.impacts:
                move = _move_at(attacker.track, t)
                impacts.append((t, cid))
                errors += _check_strike(cid, move, attacker, t, joint, fighters, sim, height, w)
        for cid, _, actor in fighters:
            for start, move in actor.track.events:
                if move in REACTIONS and not any(t - 0.15 <= start <= t + 0.05 for t, a in impacts if a != cid):
                    lands = ", ".join(f"{t:.2f}" for t, a in impacts if a != cid) or "none"
                    errors.append(f"{cid}'s {move!r} at {start:.2f} s has no strike to react to "
                                  f"(strikes land at: {lands} s)")

    # 4. Fighters never stand inside each other.
    errors += _check_overlap(fighters, w, height)

    # 5. A Fosbury flop needs its bar where the hips cross.
    errors += _check_flop(scene, fighters, w, height)
    return errors


def _check_overlap(fighters, w, height) -> list[str]:
    errors = []
    end = max(a.track.end_time for _, _, a in fighters)
    min_gap = _MIN_GAP * height
    for i, (ida, _, a) in enumerate(fighters):
        for idb, _, b in fighters[i + 1:]:
            for k in range(int(end / 0.05) + 1):
                t = k * 0.05
                gap = abs(a.track.state(t)[1] - b.track.state(t)[1])
                if gap < min_gap:
                    errors.append(f"{ida} and {idb} overlap at {t:.2f} s ({gap / w:.2f} apart); keep them at "
                                  f"least {min_gap / w:.2f} apart (e.g. 'run' to a 'to_x' further away)")
                    break
    return errors


def _check_strike(cid, move, attacker, t, joint, fighters, sim, height, w) -> list[str]:
    others = [(oid, o) for oid, _, o in fighters if o is not attacker]
    answers = [(oid, o, o.track.reaction_at(t)) for oid, o in others]
    dodging = [oid for oid, o in others if any(m == "dodge" and t - 0.3 <= s <= t for s, m in o.track.events)]
    hit = [(oid, o, r) for oid, o, r in answers if r]
    if not hit and not dodging:
        target = others[0][0]
        return [f"{cid}'s {move!r} lands at {t:.2f} s but nobody reacts: give {target} a block, dodge, "
                f"hit_react or knockback with \"at\": {t:.2f}"]
    errors = []
    x = attacker.track.state(t)[1]
    direction = 1 if attacker.track.facing_at(t) == "right" else -1
    sx, _ = sim.strike_point(attacker, t, joint)
    for oid, defender, reaction in hit:
        body_x = defender.track.state(t)[1]
        if (body_x - x) * direction < 0:
            errors.append(f"{cid} is facing away from {oid} when the {move!r} lands at {t:.2f} s")
            continue
        short = (body_x - sx) * direction  # > 0: the strike stops before the body
        if short > _FALLS_SHORT_TOLERANCE * height:
            errors.append(f"{cid}'s {move!r} at {t:.2f} s falls short of {oid} by {short / w:.2f} of the "
                          f"width; for a {move} they should be about {REACH.get(move, 0.6) * height / w:.2f} "
                          "apart when it lands (move them closer, or 'run' in first)")
    return errors


def _check_flop(scene, fighters, w, height) -> list[str]:
    bars = [p for p in scene.get("props", []) if p["kind"] == "bar"]
    errors = []
    for cid, _, actor in fighters:
        for start, move in actor.track.events:
            if move != "flop" or not bars:
                continue
            peak_t = start + MOVES["flop"].keys[3].t  # the "over the bar" key
            cross = actor.track.state(peak_t)[1]
            mat = actor.track.state(start + MOVES["flop"].duration)[1]
            if abs(bars[0]["x"] * w - cross) > 0.05 * w:
                errors.append(f"{cid}'s flop crosses x {cross / w:.2f}: put the 'bar' at x {cross / w:.2f} "
                              f"and the 'mat' at x {mat / w:.2f}")
    return errors
