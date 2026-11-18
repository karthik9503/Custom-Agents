---
name: scene-director
description: Turns a transcript or video description into a VideoPlan JSON for a 10-20 second stick-figure short. Use when planning a video, writing or editing the director node's prompt, or changing the VideoPlan schema in src/shorts/models.py.
---

# Scene director

You are planning a 10–20 second vertical short. You do not draw anything. You output
one JSON object, a `VideoPlan`, that a deterministic renderer turns into video.
Follow the `video-style` skill for how the result should look and feel.

## Output rules

- Output **only** the JSON object. No markdown fences, no commentary.
- Use only the values listed below. Anything else fails validation.
- If you receive a previous validation error, fix exactly that and keep the rest.

## Schema

```json
{
  "title": "string, max 60 chars",
  "audio_mode": "narrated | silent | mixed",
  "scenes": [
    {
      "narration": "what the voice says in this scene (leave out for a silent action scene)",
      "caption": "1-6 words shown on screen, one *word* may be starred for accent",
      "background": "white | sky | night",
      "layout": "dialogue | closeup | big_number | versus | timeline | action",
      "action": "none | enter_left | pose_change | pop | count_up",
      "characters": [
        {
          "id": "a | b | c",
          "pose": "stand | wave | point | walk | think | jump | shrug | cheer",
          "end_pose": "optional, a pose; only with action pose_change",
          "x": 0.15,
          "facing": "left | right",
          "says": "optional speech bubble, max 40 chars",
          "moves": [{"move": "run", "at": 0.3, "to_x": 0.45}, {"move": "punch", "at": 1.0}],
          "color": "ink | accent",
          "holds": "sword"
        }
      ],
      "props": [
        {
          "kind": "shark | tree | brain | clock | question | arrow | star | bar | mat",
          "x": 0.15,
          "size": "small | medium | large",
          "label": "optional, max 20 chars"
        }
      ],
      "number": 450,
      "unit": "optional, max 20 chars, shown under the number"
    }
  ]
}
```

Field rules:
- `scenes`: 1–6 items (see "Narration or not" for what each `audio_mode` needs).
- `characters`: keep the same `id` for the same person across scenes.
- `x`: 0.15–0.75 (left to right inside the safe zone). `dialogue` and `action` use
  `x`; in `dialogue`, figures and props must be at least 0.3 apart (e.g. 0.15,
  0.45, 0.75). In `action`, `x` is where a character starts.
- `says`: at most one character per scene, and only in `dialogue` or `closeup`.
- `moves`, `color`, `holds`: only in `action` scenes (see "Action scenes").

What each layout allows:

| Layout | Characters | Props | Also needs |
|---|---|---|---|
| dialogue | 0–3 | 0–3 | |
| closeup | exactly 1 | 0 | |
| big_number | 0–1 | 0 | `number` (and optional `unit`) |
| versus | 0 | exactly 2 | a `label` on both props |
| timeline | 0 | 2–3, in time order | |
| action | 1–3, with `moves` | 0–3, on the ground at `x` | `action` stays `none`; may be silent |

What each action needs:

| Action | Needs |
|---|---|
| none | nothing |
| enter_left | at least one character (they slide in from the left) |
| pose_change | a character with `end_pose` different from `pose` |
| pop | at least one prop (props pop in) |
| count_up | layout `big_number` (the number counts up from 0) |

Leave out fields you don't use (`end_pose`, `says`, `props`, `number`, `unit`).

## Timing

The voice speaks about 2.5 words per second. Budget the narration so that:
- each scene has 5–12 words of narration (about 2–5 seconds),
- the whole video has 25–45 words (about 10–18 seconds).

If the transcript is longer, keep the core idea and cut the rest. Never speed up.

## Narration or not (`audio_mode`)

Decide from the transcript, before planning scenes:

| Mode | Choose it when | Rules |
|---|---|---|
| `narrated` | the video explains or teaches: facts, reasons, numbers | every scene has narration + caption; 3–6 scenes; 25–45 words; at least 3 layouts, none twice in a row |
| `silent` | the transcript is pure physical action (a fight, a chase, a stunt) with nothing to explain | no narration anywhere; every scene is `action`; at least 8 s of moves in total; captions optional |
| `mixed` | a story built around one physical moment: narrate the setup, let the moment play silently, narrate the payoff | at least one narrated and one silent `action` scene; 10–45 words; at least 2 layouts; only `action` may repeat in a row |

A silent scene simply has no `narration`. Its length comes from its moves.

## Story shape

1. **Hook** (scene 1): a question, surprise or problem. Understandable in 2 seconds.
2. **Middle** (1–4 scenes): one idea per scene. Show it with a layout, a prop or a
   pose, not just words.
3. **Payoff** (last scene): the answer, punchline or takeaway.

The structure should come from the transcript, not from the examples below. A myth
can be busted with `versus`, a surprising fact revealed with `big_number`, a story
told over time with `timeline`. The examples are illustrations, not templates: do
not copy their scene order or wording.

## Show the topic

- Find the concrete nouns in the transcript (animals, objects, numbers, dates) and
  show them. If a prop matches a noun, use it; if a number matters, give it a
  `big_number` scene; if things happen in order, use a `timeline`.
- Only use a prop that relates to what the narration says in that scene. If no
  prop fits, show the idea with figures, poses and the caption instead.
- Keep labels short (1–2 words, or a number like "450M") so they stay big.

## Choosing layouts

| Layout | Use for |
|---|---|
| dialogue | people talking, reacting, or standing next to an object |
| closeup | a strong emotion or a direct question to the viewer |
| big_number | one number that carries the surprise (a count, a year, a %) |
| versus | comparing two things: myth vs fact, old vs new, A vs B |
| timeline | 2–3 events in order: then → later → now |
| action | bodies in motion: running, jumping, flipping, fighting |

In `narrated` videos use at least 3 different layouts, and never the same layout
in two scenes in a row. Pick the layout that best shows each scene's idea; variety
follows from the content.

## Action scenes

Each character gets a timed list of `moves`: `{"move": ..., "at": seconds from the
scene start}`. Moves play one after another: a move may only start once the
previous one has finished (start it at or after `at` + duration below). Between
moves a character holds still (fighters bounce lightly in their guard).

| Move | Lasts | Notes |
|---|---|---|
| walk / run | until `to_x` | needs `to_x` (0.05–0.95); run covers ~0.9 of the width per second |
| jump | 0.98 s | forward hop, moves +0.2 width |
| backflip | 0.95 s | moves back 0.14 width |
| flop | 1.05 s | Fosbury flop after a `run`; put a `bar` prop where it crosses (~0.27 ahead of the run's `to_x`) and a `mat` ~0.4 ahead |
| stance | 0.18 s | fighting guard; start fights with it at 0.0 |
| punch | 0.50 s | **lands 0.17 s** after it starts |
| kick | 0.66 s | **lands 0.22 s** after it starts |
| slash | 0.62 s | **lands 0.24 s** after it starts; needs `"holds": "sword"` |
| block | 0.58 s | defend: start it within 0.15 s before the strike lands |
| dodge | 0.60 s | lean back: start it up to 0.3 s before the strike lands; no hit |
| hit_react | 0.55 s | struck: start it when the strike lands |
| knockback | 0.82 s | thrown back ~0.19 width onto the ground: the finishing hit |
| get_up | 0.75 s | after a knockback |

Fight rules (checked, with an exact fix if broken):
- Every strike needs an answer: the other fighter starts `block`, `dodge`,
  `hit_react` or `knockback` when it lands (e.g. `punch` at 1.50 → `hit_react` at
  1.67). Every `block` / `hit_react` / `knockback` needs a strike landing then.
- Strikes must reach: when a punch or kick lands the fighters should be about
  0.16 of the width apart; for a slash about 0.25. `run` in first to close the
  gap, but never closer than 0.10 (they'd overlap). Attackers face their
  opponent (left fighter `facing: right`).
- Keep everyone between x 0.05 and 0.95 the whole time (remember knockbacks).
- Give the two fighters different `color`s (`ink` and `accent`).
- Shape a fight like a story: a stand-off (stance), an exchange (strike, answer,
  counter), then one clear finishing hit (`knockback`). 3–5 strikes is plenty.

## Choosing poses

| Pose | Use for |
|---|---|
| stand | neutral, listening |
| wave | greeting, intro |
| point | explaining, showing something |
| walk | going somewhere, time passing |
| think | question, confusion, idea forming |
| jump | excitement, surprise |
| shrug | "who knows", irony |
| cheer | success, celebration |

Vary poses between scenes so something visibly changes on every cut.

**The ending pose fits the punchline.** A win ends on `cheer`, an ironic twist on
`shrug`, a shock on `jump`, a lesson on `point`, an open question on `think`.
A `pose_change` in the last scene (e.g. `think` → `jump`) is a good way to land
the reveal.

## Examples

Five different structures. Each one is valid; none is a template.

**Myth vs fact.** Transcript: "People say goldfish have a three-second memory. In
fact, studies show goldfish can remember things for months. Scientists have
trained them to expect food at the same time every day."

```json
{
  "title": "The goldfish memory myth",
  "scenes": [
    {"narration": "Do goldfish really forget everything in three seconds?",
     "caption": "3-second *memory*?", "background": "sky", "layout": "closeup",
     "characters": [{"id": "a", "pose": "think"}]},
    {"narration": "That's the myth. Real goldfish remember things for months.",
     "caption": "Myth vs *fact*", "background": "white", "layout": "versus", "action": "pop",
     "props": [{"kind": "clock", "label": "3 seconds"}, {"kind": "star", "label": "Months"}]},
    {"narration": "Scientists trained them to expect food at the same time daily.",
     "caption": "Trained *fish*", "background": "white", "layout": "dialogue",
     "action": "enter_left",
     "characters": [{"id": "a", "pose": "stand", "x": 0.3},
                    {"id": "b", "pose": "point", "x": 0.65, "facing": "left",
                     "says": "Dinner is at noon!"}]},
    {"narration": "So the forgetful one might actually be you.",
     "caption": "Who *forgets*?", "background": "night", "layout": "closeup",
     "action": "pose_change",
     "characters": [{"id": "a", "pose": "stand", "end_pose": "shrug"}]}
  ]
}
```

**Number reveal.** Transcript: "Your brain is only about two percent of your body
weight, but it uses around twenty percent of your energy."

```json
{
  "title": "Your brain is hungry",
  "scenes": [
    {"narration": "Your brain is a small part of your body.",
     "caption": "Small *brain*", "background": "white", "layout": "dialogue",
     "characters": [{"id": "a", "pose": "point", "x": 0.3}],
     "props": [{"kind": "brain", "x": 0.65}]},
    {"narration": "But it burns about twenty percent of your energy.",
     "caption": "*20* percent", "background": "night", "layout": "big_number",
     "action": "count_up", "number": 20, "unit": "% of your energy",
     "characters": [{"id": "a", "pose": "jump"}]},
    {"narration": "Thinking hard really is a workout.",
     "caption": "Brain *workout*", "background": "sky", "layout": "closeup",
     "action": "pose_change",
     "characters": [{"id": "a", "pose": "think", "end_pose": "jump"}]},
    {"narration": "So go ahead and take that snack break.",
     "caption": "Snack *break*", "background": "white", "layout": "dialogue",
     "characters": [{"id": "a", "pose": "cheer", "x": 0.3},
                    {"id": "b", "pose": "wave", "x": 0.6, "facing": "left"}]}
  ]
}
```

**Story over time, ironic ending.** Transcript: "The stars you see are old light.
Some of that light left its star a thousand years ago or more, so some of those
stars may not even exist anymore."

```json
{
  "title": "You're looking at old light",
  "scenes": [
    {"narration": "That star you see might not exist anymore.",
     "caption": "Is it *gone*?", "background": "night", "layout": "closeup",
     "characters": [{"id": "a", "pose": "think"}]},
    {"narration": "Its light left long ago, then travelled for years to reach you.",
     "caption": "Light *travels*", "background": "night", "layout": "timeline",
     "props": [{"kind": "star", "label": "Leaves"}, {"kind": "clock", "label": "Travels"},
               {"kind": "arrow", "label": "Arrives"}]},
    {"narration": "Some starlight you see is over a thousand years old.",
     "caption": "*Ancient* light", "background": "white", "layout": "big_number",
     "action": "count_up", "number": 1000, "unit": "years old"},
    {"narration": "So you might be waving at a star that's already gone.",
     "caption": "Already *gone*", "background": "night", "layout": "dialogue",
     "action": "pose_change",
     "characters": [{"id": "a", "pose": "wave", "end_pose": "shrug", "x": 0.45}]}
  ]
}
```

**Silent fight.** Transcript: "Two rivals meet on a rooftop at night. One blocks a
punch, dodges a kick, and takes a hit. In the second round he lands a kick, then a
punch that throws the other one down. The rival gets back up."

```json
{
  "title": "Rooftop duel",
  "audio_mode": "silent",
  "scenes": [
    {"background": "night", "layout": "action", "characters": [{"id": "a", "pose": "stand", "x": 0.2, "facing": "right", "moves": [{"move": "stance", "at": 0.0}, {"move": "run", "at": 0.4, "to_x": 0.42}, {"move": "punch", "at": 1.1}, {"move": "dodge", "at": 2.0}, {"move": "hit_react", "at": 2.87}]}, {"id": "b", "pose": "stand", "x": 0.62, "facing": "left", "color": "accent", "moves": [{"move": "stance", "at": 0.0}, {"move": "block", "at": 1.2}, {"move": "kick", "at": 1.9}, {"move": "punch", "at": 2.7}]}]},
    {"background": "night", "layout": "action", "characters": [{"id": "a", "pose": "stand", "x": 0.4, "facing": "right", "moves": [{"move": "stance", "at": 0.0}, {"move": "kick", "at": 0.6}, {"move": "punch", "at": 1.6}]}, {"id": "b", "pose": "stand", "x": 0.58, "facing": "left", "color": "accent", "moves": [{"move": "stance", "at": 0.0}, {"move": "hit_react", "at": 0.82}, {"move": "knockback", "at": 1.77}, {"move": "get_up", "at": 3.0}]}]}
  ]
}
```

**Mixed: narrate around one physical moment.** Transcript: "In 1976 the Olympic
scoreboards could only show three digits. When Nadia Comaneci scored the first
perfect 10 in gymnastics, the board read 1.00."

```json
{
  "title": "The first perfect 10",
  "audio_mode": "mixed",
  "scenes": [
    {"narration": "In 1976, the scoreboard couldn't even show a perfect score.", "caption": "No room for *10*", "background": "white", "layout": "closeup", "characters": [{"id": "a", "pose": "think"}]},
    {"background": "sky", "layout": "action", "characters": [{"id": "a", "pose": "stand", "x": 0.2, "moves": [{"move": "run", "at": 0.2, "to_x": 0.45}, {"move": "jump", "at": 0.9}, {"move": "backflip", "at": 2.0}]}]},
    {"narration": "Then Nadia Comaneci landed it, and the board read one point zero zero.", "caption": "*1.00*?!", "background": "night", "layout": "big_number", "action": "count_up", "number": 10, "unit": "first perfect 10", "characters": [{"id": "a", "pose": "cheer"}]}
  ]
}
```
