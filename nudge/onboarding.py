"""The 10-minute onboarding chat.

This is the training phase. The AI acts like a relaxed, curious friend getting to
know you — NOT a form. While it chats, it's quietly collecting two things:
  1. how you write (style)
  2. what's going on in your life worth nudging (memory + targets)

The style is captured implicitly: we never ask "do you use slang?" — we just let
you talk and read it off your messages later (see extract.py). Asking directly
would make people self-conscious and flatten their natural voice.
"""
from __future__ import annotations

from .config import SETTINGS
from .llm import GeminiClient

ONBOARDING_SYSTEM = """\
You are the onboarding host for a reminder app. Your job is to have a short, \
natural, friendly conversation (aim ~8-12 exchanges) to get to know the user.

Behave like a warm, curious friend — not an interviewer and definitely not a form.
- Ask ONE question at a time. Keep your own messages short.
- React to what they say before moving on ("oof, that sounds rough"). Be human.
- Mirror their energy a little, but stay lightly neutral in YOUR style so you don't
  contaminate the sample of how THEY naturally write.

Cover, naturally and in any order:
- their rough daily rhythm (wake, work/study, wind-down, sleep)
- 2-4 things they keep meaning to do but slip on (the "targets")
- the *why* behind each — the real reason it matters to them (this is important)
- anything going on lately worth a mental note (stress, a hard week, a new routine)

Hard rules:
- Never lecture or give health/medical/clinical advice.
- If they mention something heavy (self-harm, crisis), drop the app persona, gently
  point them to appropriate help (e.g. 988 in the US), and do not push app tasks.
- Do NOT announce that you're profiling them or analyzing their writing.

When you sense you have enough (schedule + a few targets with reasons), wrap up warmly
and end your final message with the token <<DONE>> on its own line.
"""


class OnboardingSession:
    def __init__(self, client: GeminiClient):
        self.client = client
        self.transcript: list[tuple[str, str]] = []  # (role, text), role in {"ai","user"}

    def _history_block(self) -> str:
        lines = []
        for role, text in self.transcript:
            who = "HOST" if role == "ai" else "USER"
            lines.append(f"{who}: {text}")
        return "\n".join(lines)

    def opening_line(self) -> str:
        msg = ("hey! i'm gonna be the one nudging you, so i wanna actually know you a "
               "bit first — no forms, just chatting. what's a normal day look like for you?")
        self.transcript.append(("ai", msg))
        return msg

    def user_says(self, text: str) -> str:
        """Record the user's message, return the host's next reply."""
        self.transcript.append(("user", text))
        prompt = (
            f"Conversation so far:\n{self._history_block()}\n\n"
            "Write ONLY the host's next message."
        )
        reply = self.client.generate(
            model=SETTINGS.onboarding_model,
            prompt=prompt,
            system=ONBOARDING_SYSTEM,
            temperature=0.8,
        )
        self.transcript.append(("ai", reply))
        return reply

    @property
    def is_done(self) -> bool:
        return bool(self.transcript) and "<<DONE>>" in self.transcript[-1][1]

    def user_transcript_text(self) -> str:
        """Just the USER's lines — the raw material for style extraction."""
        return "\n".join(t for r, t in self.transcript if r == "user")
