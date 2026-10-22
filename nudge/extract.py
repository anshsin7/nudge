"""Turn an onboarding transcript into a structured UserProfile (JSON).

Two signals come from the transcript:
  - STYLE is read off the user's *own* messages (their raw text is the ground truth).
  - MEMORY + TARGETS are the facts they shared.

We ask the model for strict JSON (json_mode) matching the schema, then parse it
through UserProfile.from_dict so a malformed field can't crash the pipeline.
"""
from __future__ import annotations

import json

from .config import SETTINGS
from .llm import GeminiClient, LLMError
from .schema import UserProfile

EXTRACT_SYSTEM = """\
You extract a structured user profile from an onboarding chat transcript.
Return ONLY valid JSON. No prose, no markdown fences.

Analyze the USER's own messages to infer writing style. Be faithful to how THEY
write, not how the host wrote.

Schema:
{
  "user_id": string,
  "style": {
    "tone": one of ["casual","casual_sarcastic","warm","direct","energetic","gentle"],
    "capitalization": boolean,          // true if they capitalize normally
    "emoji_frequency": one of ["none","low","medium","high"],
    "slang": [string],                  // actual slang/abbreviations THEY used
    "avg_sentence_length": integer,     // rough words per message
    "punctuation_quirks": [string]      // e.g. "no_periods","ellipses","all_lowercase","exclamations"
  },
  "memory": {
    "schedule": { "wake": "HH:MM", "sleep": "HH:MM", ... },
    "recent_notes": [string],           // specific things going on lately
    "pain_points": [string]
  },
  "targets": [
    { "goal": string, "context": string, "preferred_window": string }
  ],
  "voice": "friend"
}

Rules:
- Only include slang the user actually used. Do not invent a persona.
- context on each target = the real reason it matters to them (their words/ideas).
- If something is unknown, use an empty string/array — never guess wildly.
"""


def extract_profile(
    client: GeminiClient, user_id: str, user_text: str, full_transcript: str
) -> UserProfile:
    prompt = (
        f"user_id: {user_id}\n\n"
        f"=== USER MESSAGES (use these for STYLE) ===\n{user_text}\n\n"
        f"=== FULL TRANSCRIPT (use for MEMORY + TARGETS) ===\n{full_transcript}\n\n"
        "Return the profile JSON now."
    )
    raw = client.generate(
        model=SETTINGS.extract_model,
        prompt=prompt,
        system=EXTRACT_SYSTEM,
        json_mode=True,
        temperature=0.2,  # extraction wants consistency, not creativity
    )
    data = _safe_json(raw)
    data.setdefault("user_id", user_id)
    return UserProfile.from_dict(data)


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    # strip accidental ```json fences
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].removeprefix("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(f"Extractor returned non-JSON:\n{raw[:400]}") from e
