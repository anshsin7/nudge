#!/usr/bin/env python3
"""Run the whole vertical slice end-to-end from the terminal.

    python demo.py            # live, needs GEMINI_API_KEY
    python demo.py --mock     # no key / no network — see the shapes and flow
    python demo.py --auto     # scripted user answers (good for a quick live check)

The point of this file: let you *feel* the output quality before we build any
app or push infrastructure around it.
"""
from __future__ import annotations

import argparse
import sys

from nudge.llm import GeminiClient, LLMError
from nudge.onboarding import OnboardingSession
from nudge.extract import extract_profile
from nudge.generate import generate_nudges

# Scripted answers for --auto so a live run needs no typing.
SCRIPTED = [
    "honestly pretty chaotic lol. up around 8, work from home til like 6, "
    "then i just kinda vibe until i crash way too late",
    "ngl i keep forgetting to drink water during the day and then i get these "
    "brutal headaches by the afternoon",
    "and the big one, i doomscroll in bed til like 1am and it wrecks my sleep. "
    "trying to cut it at 11 but lol",
    "my back's been killing me too, got a standing desk but i overdid it today fr",
    "yeah that's basically it. wake ~8, bed should be 11 but it's never 11",
]


def banner(t: str) -> None:
    print(f"\n{'=' * 62}\n  {t}\n{'=' * 62}")


def run(mock: bool, auto: bool) -> int:
    try:
        client = GeminiClient(mock=mock)
    except LLMError as e:
        print(f"[setup] {e}", file=sys.stderr)
        return 1

    banner("1. ONBOARDING CHAT")
    session = OnboardingSession(client)
    print(f"host> {session.opening_line()}")

    try:
        if auto or mock:
            for line in SCRIPTED:
                print(f"you > {line}")
                reply = session.user_says(line)
                print(f"host> {reply}")
                if session.is_done:
                    break
        else:
            while not session.is_done:
                try:
                    line = input("you > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if not line:
                    continue
                if line.lower() in {"/done", "quit", "exit"}:
                    break
                print(f"host> {session.user_says(line)}")

        banner("2. EXTRACTED PROFILE")
        profile = extract_profile(
            client,
            user_id="demo",
            user_text=session.user_transcript_text(),
            full_transcript="\n".join(f"{r}: {t}" for r, t in session.transcript),
        )
        print(profile.to_json())

        banner("3. GENERATED NUDGES (in their voice)")
        if not profile.targets:
            print("(no targets extracted — nothing to nudge)")
            return 0
        for target in profile.targets:
            print(f"\n-- goal: {target.goal}"
                  f"{f'  (because: {target.context})' if target.context else ''}")
            for nudge in generate_nudges(client, profile, target):
                print(f"   • {nudge}")
    except LLMError as e:
        print(f"\n[llm] {e}", file=sys.stderr)
        return 1

    banner("done")
    print("This is the brain only — no app/push yet, by design. "
          "Tune the prompts in nudge/ until the nudges feel human.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="no API calls; show flow + shapes")
    ap.add_argument("--auto", action="store_true", help="use scripted answers (live)")
    args = ap.parse_args()
    raise SystemExit(run(mock=args.mock, auto=args.auto))
