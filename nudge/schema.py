"""The data contract.

`StyleProfile` captures *how* a user writes; `Memory` captures *what's going on*
with them. The second is what keeps nudges from going stale — slang alone gets
old by day three; specific context ("standing-desk day was brutal") does not.

Kept as plain dataclasses (no pydantic) so the slice has one dependency.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Tone(str, Enum):
    CASUAL = "casual"
    CASUAL_SARCASTIC = "casual_sarcastic"
    WARM = "warm"
    DIRECT = "direct"
    ENERGETIC = "energetic"
    GENTLE = "gentle"


class Voice(str, Enum):
    FRIEND = "friend"       # ships in V1
    INNER = "inner_voice"   # opt-in, guarded


class EmojiFreq(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class StyleProfile:
    tone: Tone = Tone.CASUAL
    capitalization: bool = True            # does the user capitalize normally?
    emoji_frequency: EmojiFreq = EmojiFreq.LOW
    slang: list[str] = field(default_factory=list)   # e.g. ["fr", "lowkey", "imo"]
    avg_sentence_length: int = 8           # in words, rough
    punctuation_quirks: list[str] = field(default_factory=list)  # ["ellipses", "no_periods"]


@dataclass
class Target:
    """A habit the user wants nudged, plus the *why* behind it (context is gold)."""
    goal: str                              # "drink water"
    context: str = ""                      # "gets headaches when dehydrated"
    preferred_window: str = ""             # "afternoons", "11pm"


@dataclass
class Memory:
    """Specific, personal facts the nudge engine can reference. This is the moat."""
    schedule: dict[str, str] = field(default_factory=dict)   # {"wake":"7:30","sleep":"23:30"}
    recent_notes: list[str] = field(default_factory=list)    # ["standing-desk day was brutal"]
    pain_points: list[str] = field(default_factory=list)     # ["avoids studying","forgets keys"]


@dataclass
class UserProfile:
    user_id: str
    style: StyleProfile = field(default_factory=StyleProfile)
    memory: Memory = field(default_factory=Memory)
    targets: list[Target] = field(default_factory=list)
    voice: Voice = Voice.FRIEND

    # ---- (de)serialization -------------------------------------------------
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, default=_enum_default)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UserProfile":
        style = StyleProfile(
            tone=Tone(d.get("style", {}).get("tone", "casual")),
            capitalization=d.get("style", {}).get("capitalization", True),
            emoji_frequency=EmojiFreq(d.get("style", {}).get("emoji_frequency", "low")),
            slang=d.get("style", {}).get("slang", []),
            avg_sentence_length=d.get("style", {}).get("avg_sentence_length", 8),
            punctuation_quirks=d.get("style", {}).get("punctuation_quirks", []),
        )
        memory = Memory(
            schedule=d.get("memory", {}).get("schedule", {}),
            recent_notes=d.get("memory", {}).get("recent_notes", []),
            pain_points=d.get("memory", {}).get("pain_points", []),
        )
        targets = [
            Target(goal=t.get("goal", ""), context=t.get("context", ""),
                   preferred_window=t.get("preferred_window", ""))
            for t in d.get("targets", [])
        ]
        return cls(
            user_id=d.get("user_id", "unknown"),
            style=style, memory=memory, targets=targets,
            voice=Voice(d.get("voice", "friend")),
        )


def _enum_default(o: Any):
    if isinstance(o, Enum):
        return o.value
    raise TypeError(f"not serializable: {type(o)}")
