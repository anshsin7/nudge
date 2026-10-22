"""Thin wrapper around the Google Gen AI SDK.

Why a wrapper:
  - one place to stub for offline/mock runs (no API key needed to see the flow)
  - one place to swap SDK/provider later without touching prompt logic
  - isolates the "legacy vs new API" churn — we use generate_content, which Google
    now labels "Legacy" but which remains stable and is the right call for a prototype.

SDK shape (google-genai):
    from google import genai
    client = genai.Client(api_key=...)
    client.models.generate_content(model=..., contents=..., config=...)
"""
from __future__ import annotations

from .config import SETTINGS


class LLMError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str | None = None, mock: bool = False):
        self.mock = mock
        self._client = None
        if mock:
            return
        key = api_key or SETTINGS.api_key
        if not key:
            raise LLMError(
                "No GEMINI_API_KEY set. Export one, or run the demo with --mock."
            )
        try:
            from google import genai  # imported lazily so --mock needs no install
        except ImportError as e:
            raise LLMError(
                "google-genai not installed. `pip install -r requirements.txt` "
                "or run with --mock."
            ) from e
        self._client = genai.Client(api_key=key)

    def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.9,
    ) -> str:
        if self.mock:
            return _mock_response(prompt, system, json_mode)

        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json" if json_mode else None,
        )
        try:
            resp = self._client.models.generate_content(
                model=model, contents=prompt, config=cfg
            )
        except Exception as e:  # network / quota / safety blocks
            raise LLMError(f"Gemini call failed: {e}") from e
        return (resp.text or "").strip()


def _mock_response(prompt: str, system: str | None, json_mode: bool) -> str:
    """Deterministic-ish stand-ins so the pipeline runs with no API key."""
    if json_mode and "extract" in (system or "").lower():
        return (
            '{"user_id":"demo","style":{"tone":"casual_sarcastic",'
            '"capitalization":false,"emoji_frequency":"low",'
            '"slang":["lowkey","fr","ngl"],"avg_sentence_length":6,'
            '"punctuation_quirks":["no_periods"]},'
            '"memory":{"schedule":{"wake":"08:00","sleep":"23:30"},'
            '"recent_notes":["standing-desk day wrecked my back"],'
            '"pain_points":["doomscrolls past midnight","forgets to drink water"]},'
            '"targets":[{"goal":"drink water","context":"gets headaches when dehydrated",'
            '"preferred_window":"afternoons"},'
            '{"goal":"stop scrolling at 11pm","context":"wrecks sleep","preferred_window":"23:00"}],'
            '"voice":"friend"}'
        )
    if json_mode:  # nudge generation
        return (
            '["lowkey go grab water before ur head starts pounding again",'
            '"water check. u have not moved from that desk in forever ngl",'
            '"hydrate real quick, the back pain already called u once today",'
            '"ok but when did u last drink water. be honest",'
            '"little water break, future u says thanks fr"]'
        )
    # onboarding chat turn
    return "haha fair. so walk me through a normal weekday for you — when do you usually wake up?"
