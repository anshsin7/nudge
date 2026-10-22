"""Central config. Model names live here because Gemini's free-tier model IDs
change often — swap them in one place when they rotate.

As of late 2026 the free text models are gemini-3.8-flash and
gemini-3.5-flash-lite. See README for context.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Stronger model for the nuanced work: interviewing + pattern extraction.
    onboarding_model: str = "gemini-3.8-flash"
    extract_model: str = "gemini-3.8-flash"

    # Cheap + fast + high rate limit for churning out nudge candidates.
    generate_model: str = "gemini-3.5-flash-lite"

    # How many candidate nudges to pre-generate per trigger window.
    nudge_pool_size: int = 5

    # Keep daily frequency low — a friend texting you 15x/day is not a friend.
    max_nudges_per_day: int = 5

    # "inner voice" mimicry is powerful but easy to make uncanny; gate it.
    allow_inner_voice: bool = False

    @property
    def api_key(self) -> str | None:
        return os.environ.get("GEMINI_API_KEY")


SETTINGS = Settings()
