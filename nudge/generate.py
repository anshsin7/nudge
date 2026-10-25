"""Turn a profile + a trigger into a *batch* of candidate nudges.

Why a batch, not one-at-a-time-live:
  - keeps live inference off the notification critical path (latency + cost)
  - lets a safety pass filter candidates BEFORE anything could reach a lock screen
  - gives variation for free — the scheduler picks one and parks the rest

The prompt's whole job is: say the reminder the way THIS person would say it to
themselves, referencing what they actually told us.
"""
from __future__ import annotations

import json
import re

from .config import SETTINGS
from .llm import GeminiClient, LLMError
from .schema import UserProfile, Target, Voice

GENERATE_SYSTEM = """\
You write short phone-notification reminders that sound exactly like a specific \
person's close friend — the kind of friend who's a bit of a menace but clearly \
has your back — texting them. The audience is Gen Z; the texts should feel like \
a real group-chat message, not an app.

You are given a STYLE PROFILE and some MEMORY. Match the style precisely:
capitalization, slang, emoji frequency, sentence length, punctuation quirks.

Make each nudge:
- short (fits a lock screen — one line, ~4-14 words)
- reference the SPECIFIC goal and, when natural, the personal reason/context
- feel fresh and varied — never a template, never corporate ("Time to...")
- land like a nudge from someone who cares, lightly roasting > scolding

Gen Z texting craft (match the user's profile; don't force any of these):
- lowercase by default unless the profile says they capitalize
- dry, deadpan, slightly chaotic humor; understatement over hype
- natural slang only — use the slang THEY actually used in `slang`; do not pile on
  extra slang they never said
- it's fine to be a little unhinged/affectionate ("bestie no", "babe. water.")
- questions and callouts land well ("when did you last drink water. be honest")

ANTI-CRINGE RULES (most important — breaking these ruins it):
- Do NOT try too hard. One slang term per message is usually plenty.
- NEVER use dated/boomer-ified slang or hashtags: no "YOLO", "on fleek", "#blessed",
  "hello fellow kids" energy, no explaining the joke.
- Don't stack 3+ emojis. Don't use emojis at all if emoji_frequency is "none"/"low".
- If in doubt, fewer words + drier tone. Cringe comes from effort showing.

Hard rules:
- No health/medical claims or diagnoses. No guilt-tripping or shaming.
- Nothing mean, anxiety-inducing, or about appearance/weight/calories.
- Keep it to the one goal given.

Return ONLY a JSON array of strings. No prose, no fences.
"""


def _voice_note(profile: UserProfile) -> str:
    if profile.voice == Voice.INNER and SETTINGS.allow_inner_voice:
        return "Voice: the user's OWN inner monologue (first person, talking to self)."
    return "Voice: a close friend texting them (second person)."


def generate_nudges(
    client: GeminiClient, profile: UserProfile, target: Target, n: int | None = None
) -> list[str]:
    n = n or SETTINGS.nudge_pool_size
    s = profile.style
    prompt = (
        f"{_voice_note(profile)}\n\n"
        f"STYLE PROFILE:\n"
        f"- tone: {s.tone.value}\n"
        f"- capitalization: {s.capitalization}\n"
        f"- emoji_frequency: {s.emoji_frequency.value}\n"
        f"- slang they use: {s.slang}\n"
        f"- avg words/msg: {s.avg_sentence_length}\n"
        f"- quirks: {s.punctuation_quirks}\n\n"
        f"MEMORY:\n"
        f"- recent: {profile.memory.recent_notes}\n"
        f"- pain points: {profile.memory.pain_points}\n\n"
        f"GOAL TO NUDGE: {target.goal}\n"
        f"WHY IT MATTERS TO THEM: {target.context or '(unknown)'}\n\n"
        f"Write {n} distinct nudges as a JSON array of strings."
    )
    raw = client.generate(
        model=SETTINGS.generate_model,
        prompt=prompt,
        system=GENERATE_SYSTEM,
        json_mode=True,
        temperature=1.0,  # we want variety here
    )
    candidates = _parse_array(raw)
    return [c for c in candidates if is_safe(c) and not is_cringe(c)]


# ---- safety pass ----------------------------------------------------------
# Cheap deterministic backstop so a bad-tone generation never reaches a user.
# Intentionally conservative; a real system would add a model-based classifier.
_BANNED = re.compile(
    r"\b(kill|die|worthless|stupid|fat|ugly|lazy piece|hate yourself|loser)\b",
    re.IGNORECASE,
)

# Dated / try-hard slang that instantly reads as "adult pretending to be Gen Z".
# A nudge containing these is dropped from the pool.
_CRINGE = re.compile(
    r"\b(yolo|on fleek|bae|swag|totes|amazeballs|hello fellow kids|epic win|"
    r"groovy|hashtag|#\w+)\b",
    re.IGNORECASE,
)


def is_safe(text: str) -> bool:
    if not text or len(text) > 180:
        return False
    if _BANNED.search(text):
        return False
    return True


def is_cringe(text: str) -> bool:
    """True if the nudge reads as try-hard/dated — filtered out of the pool."""
    if _CRINGE.search(text):
        return True
    # too many emoji stacked = trying too hard
    emoji = sum(1 for ch in text if ord(ch) > 0x2190)
    return emoji >= 3


def _parse_array(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].removeprefix("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(f"Generator returned non-JSON:\n{raw[:400]}") from e
    if not isinstance(data, list):
        raise LLMError("Generator did not return a JSON array.")
    return [str(x).strip() for x in data if str(x).strip()]
