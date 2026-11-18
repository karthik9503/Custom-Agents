"""Pydantic models for the VideoPlan the director produces.

The allowed values mirror the schema in .claude/skills/scene-director/SKILL.md.
If you change one, change the other (tests/test_models.py checks the lists).
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- Catalogs: the single place each list of names lives. -------------------
# To add a value: add it here, teach the renderer to draw it, and list it in
# the scene-director skill. Tests fail until all three agree.
LAYOUTS = ("dialogue", "closeup", "big_number", "versus", "timeline", "action")
ACTIONS = ("none", "enter_left", "pose_change", "pop", "count_up")
PROP_KINDS = ("shark", "tree", "brain", "clock", "question", "arrow", "star", "bar", "mat")
# Moves a character can do in an "action" scene (render/moves.py MOVES).
ACTION_MOVES = ("walk", "run", "jump", "backflip", "flop", "stance", "punch", "kick", "slash",
                "block", "dodge", "hit_react", "knockback", "get_up")
TRAVEL_MOVES = ("walk", "run")  # these need a target `to_x`
AUDIO_MODES = ("narrated", "silent", "mixed")

Pose = Literal["stand", "wave", "point", "walk", "think", "jump", "shrug", "cheer"]
Background = Literal["white", "sky", "night"]
Layout = Literal[LAYOUTS]
Action = Literal[ACTIONS]
PropKind = Literal[PROP_KINDS]
MoveName = Literal[ACTION_MOVES]
AudioMode = Literal[AUDIO_MODES]

# How many characters and props each layout can show: (min, max).
LAYOUT_LIMITS: dict[str, dict[str, tuple[int, int]]] = {
    "dialogue":   {"characters": (0, 3), "props": (0, 3)},
    "closeup":    {"characters": (1, 1), "props": (0, 0)},
    "big_number": {"characters": (0, 1), "props": (0, 0)},
    "versus":     {"characters": (0, 0), "props": (2, 2)},
    "timeline":   {"characters": (0, 0), "props": (2, 3)},
    "action":     {"characters": (1, 3), "props": (0, 3)},
}
BUBBLE_LAYOUTS = ("dialogue", "closeup")  # layouts with room for a speech bubble

# A pointing arm or a large tree reaches ~0.15 of the width from its center, so
# neighbours need 0.3 between centers to never touch.
MIN_FIGURE_GAP = 0.3
MIN_TOTAL_WORDS = 25
MAX_TOTAL_WORDS = 45
MIN_MIXED_WORDS = 10  # mixed videos: the action carries part of the story
MAX_CAPTION_WORDS = 6
MIN_DISTINCT_LAYOUTS = 3
MIN_SILENT_SECONDS = 8  # a silent video must have this much action

# Matches one *starred* span in a caption.
STAR_RE = re.compile(r"\*[^*]+\*")


def count_words(text: str) -> int:
    return len(text.split())


class MoveStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    move: MoveName
    at: float = Field(ge=0, le=8)  # seconds after the scene starts
    to_x: float | None = Field(default=None, ge=0.05, le=0.95)  # walk/run target

    @model_validator(mode="after")
    def check_target(self) -> "MoveStep":
        if self.move in TRAVEL_MOVES and self.to_x is None:
            raise ValueError(f"move {self.move!r} needs a 'to_x' target")
        if self.move not in TRAVEL_MOVES and self.to_x is not None:
            raise ValueError(f"'to_x' is only used by {TRAVEL_MOVES}, not {self.move!r}")
        return self


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["a", "b", "c"]
    pose: Pose
    end_pose: Pose | None = None  # only with action "pose_change"
    x: float = Field(default=0.45, ge=0.15, le=0.75)
    facing: Literal["left", "right"] = "right"
    says: str | None = Field(default=None, max_length=40)
    # "action" layout only:
    moves: list[MoveStep] = Field(default_factory=list, max_length=12)
    color: Literal["ink", "accent"] = "ink"
    holds: Literal["sword"] | None = None


class Prop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PropKind
    x: float = Field(default=0.45, ge=0.15, le=0.75)  # used by "dialogue"; others place props
    size: Literal["small", "medium", "large"] = "medium"
    label: str | None = Field(default=None, max_length=20)


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narration: str | None = Field(default=None, min_length=1)  # None: a silent scene
    caption: str | None = Field(default=None, min_length=1)    # required when narrated
    background: Background
    layout: Layout
    action: Action = "none"
    characters: list[Character] = Field(default_factory=list, max_length=3)
    props: list[Prop] = Field(default_factory=list, max_length=3)
    number: float | None = None  # big_number only
    unit: str | None = Field(default=None, max_length=20)  # shown under the number

    @model_validator(mode="after")
    def check_scene(self) -> "Scene":
        self._check_caption()
        self._check_layout()
        self._check_action()
        self._check_spacing()
        self._check_choreography()
        return self

    def _check_caption(self) -> None:
        if self.caption is None:
            if self.narration:
                raise ValueError("a narrated scene needs a 'caption'")
            return
        words = count_words(self.caption.replace("*", ""))
        if not 1 <= words <= MAX_CAPTION_WORDS:
            raise ValueError(f"caption must be 1-{MAX_CAPTION_WORDS} words, got {words}: {self.caption!r}")
        if self.caption.count("*") % 2 or len(STAR_RE.findall(self.caption)) > 1:
            raise ValueError(f"caption may star at most one *word*: {self.caption!r}")

    def _check_layout(self) -> None:
        limits = LAYOUT_LIMITS[self.layout]
        for field in ("characters", "props"):
            lo, hi = limits[field]
            n = len(getattr(self, field))
            if not lo <= n <= hi:
                allowed = f"exactly {lo}" if lo == hi else f"{lo}-{hi}"
                raise ValueError(f"layout {self.layout!r} needs {allowed} {field}, got {n}")

        if self.layout == "big_number" and self.number is None:
            raise ValueError("layout 'big_number' needs a 'number'")
        if self.layout != "big_number" and (self.number is not None or self.unit):
            raise ValueError("'number' and 'unit' are only used by layout 'big_number'")
        if self.layout == "versus" and not all(p.label for p in self.props):
            raise ValueError("layout 'versus' needs a 'label' on both props")

        speakers = [c for c in self.characters if c.says]
        if len(speakers) > 1:
            raise ValueError("at most one character per scene may have a 'says' bubble")
        if speakers and self.layout not in BUBBLE_LAYOUTS:
            raise ValueError(f"'says' bubbles only fit layouts {BUBBLE_LAYOUTS}, not {self.layout!r}")

        ids = [c.id for c in self.characters]
        if len(ids) != len(set(ids)):
            raise ValueError(f"character ids must be unique within a scene: {ids}")

        if self.layout != "action" and any(c.moves or c.holds or c.color != "ink" for c in self.characters):
            raise ValueError("'moves', 'holds' and 'color' are only used by layout 'action'")
        if self.layout == "action" and self.action != "none":
            raise ValueError("layout 'action' uses each character's 'moves', not a scene 'action'")
        if self.layout == "action" and not any(c.moves for c in self.characters):
            raise ValueError("layout 'action' needs at least one character with 'moves'")
        if self.layout != "action" and not self.narration:
            raise ValueError(f"only layout 'action' can be silent; layout {self.layout!r} needs 'narration'")

    def _check_action(self) -> None:
        changers = [c for c in self.characters if c.end_pose]
        if self.action == "pose_change":
            if not changers:
                raise ValueError("action 'pose_change' needs a character with an 'end_pose'")
            if any(c.end_pose == c.pose for c in changers):
                raise ValueError("'end_pose' must differ from 'pose'")
        elif changers:
            raise ValueError("'end_pose' is only allowed with action 'pose_change'")

        if self.action == "enter_left" and not self.characters:
            raise ValueError("action 'enter_left' needs at least one character")
        if self.action == "pop" and not self.props:
            raise ValueError("action 'pop' needs at least one prop")
        if self.action == "count_up" and self.layout != "big_number":
            raise ValueError("action 'count_up' only works with layout 'big_number'")

    def _check_spacing(self) -> None:
        # Only "dialogue" places things by x; everything on the floor must not overlap.
        if self.layout != "dialogue":
            return
        xs = sorted([c.x for c in self.characters] + [p.x for p in self.props])
        for left, right in zip(xs, xs[1:]):
            # Small tolerance: 0.75 - 0.45 is 0.29999... in floating point.
            if right - left < MIN_FIGURE_GAP - 1e-9:
                raise ValueError(
                    f"in 'dialogue', figures and props must be at least {MIN_FIGURE_GAP} apart in x, got {xs}"
                )

    def _check_choreography(self) -> None:
        if self.layout != "action":
            return
        # Imported here: the check simulates the fight with the real move library.
        from shorts.render.choreo import check_scene

        errors = check_scene(self.model_dump())
        if errors:
            raise ValueError("; ".join(errors[:3]))


class VideoPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=60)
    audio_mode: AudioMode = "narrated"
    scenes: list[Scene] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def check_plan(self) -> "VideoPlan":
        narrated = [s for s in self.scenes if s.narration]
        silent = [s for s in self.scenes if not s.narration]
        words = sum(count_words(s.narration) for s in narrated)
        layouts = [s.layout for s in self.scenes]

        if self.audio_mode == "narrated":
            if silent:
                raise ValueError("audio_mode 'narrated': every scene needs 'narration' "
                                 "(use 'mixed' for silent action scenes)")
            if len(self.scenes) < 3:
                raise ValueError("audio_mode 'narrated' needs at least 3 scenes")
            self._check_words(words, MIN_TOTAL_WORDS)
            self._check_variety(layouts, MIN_DISTINCT_LAYOUTS, allow_repeat=())
        elif self.audio_mode == "silent":
            if narrated:
                raise ValueError("audio_mode 'silent': no scene may have 'narration'")
            self._check_silent_length()
        else:  # mixed
            if not narrated or not silent:
                raise ValueError("audio_mode 'mixed' needs at least one narrated and one silent scene")
            self._check_words(words, MIN_MIXED_WORDS)
            # Two action scenes in a row are fine (one fight, two beats).
            self._check_variety(layouts, 2, allow_repeat=("action",))
        return self

    @staticmethod
    def _check_words(words: int, minimum: int) -> None:
        if not minimum <= words <= MAX_TOTAL_WORDS:
            raise ValueError(f"total narration must be {minimum}-{MAX_TOTAL_WORDS} words, got {words}")

    @staticmethod
    def _check_variety(layouts: list[str], distinct: int, allow_repeat: tuple[str, ...]) -> None:
        if len(set(layouts)) < distinct:
            raise ValueError(f"use at least {distinct} different layouts per video, got {layouts}")
        for i, (a, b) in enumerate(zip(layouts, layouts[1:])):
            if a == b and a not in allow_repeat:
                raise ValueError(f"scenes {i} and {i + 1} both use layout {a!r}; vary layouts between scenes")

    def _check_silent_length(self) -> None:
        from shorts.render.choreo import scene_length

        total = sum(scene_length(s.model_dump()) for s in self.scenes)
        if total < MIN_SILENT_SECONDS:
            raise ValueError(f"a silent video needs at least {MIN_SILENT_SECONDS} s of action, "
                             f"got {total:.1f} s: add more moves")
