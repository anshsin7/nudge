# nudge — reminders that sound like *you*

A prototype for an AI reminder app whose notifications don't sound like a robot.
They sound like a friend who knows you — or like your own brain talking back.

> **Status: vertical slice.** This repo is intentionally *just the brain* — no mobile
> app, no push infrastructure yet. The goal is to iterate on whether the generated
> nudges actually *feel* human before building anything around them.

## The idea

Instead of `"Time to drink water and take a break."`
you get `"bro lowkey go drink water before ur head starts hurting again"`.

The trick is two things working together:
1. **Style** — *how* you text (lowercase? slang? emoji? short + punchy?).
2. **Memory** — *what's actually going on with you* (the standing-desk day was brutal,
   you're trying to stop scrolling at 11pm). This is what keeps nudges from going stale.

## Pipeline

```
[ onboarding chat ]  ->  [ extract profile ]  ->  [ profile + memory JSON ]
                                                          |
                              [ trigger ]  ->  [ generate nudges ]  ->  pool of nudges
```

## What's here

| Module | Purpose |
|---|---|
| `nudge/config.py`       | Model names + settings (swap models in one place). |
| `nudge/schema.py`       | The `StyleProfile` / `Memory` data model (the contract). |
| `nudge/llm.py`          | Thin Gemini client wrapper (easy to stub/swap). |
| `nudge/onboarding.py`   | The interviewer system prompt + chat loop. |
| `nudge/extract.py`      | Turns a chat transcript into a profile JSON. |
| `nudge/generate.py`     | Turns a profile + trigger into a *batch* of candidate nudges. |
| `demo.py`               | Run the whole slice end-to-end from the terminal. |

## Why Gemini (for now)

Generous free tier — we can iterate on prompt quality without spending money yet.
Models are pinned in `nudge/config.py` because Gemini's free-tier model names change
often; as of late 2026 the free text models are `gemini-3.8-flash` and
`gemini-3.5-flash-lite`.

## Design decisions worth knowing

- **Batch pre-generation, not live-per-notification.** We generate a *pool* of candidate
  nudges ahead of a trigger window. Keeps live inference off the critical path (latency,
  cost, and a bad-tone message hitting a lock screen with no safety net).
- **"Friend voice" ships first; "inner voice" is opt-in.** Mimicking someone's inner
  monologue is the most compelling pitch but the easiest to make uncanny, so it's gated.
- **A safety pass filters nudges** before they'd ever be sent (see `generate.py`).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-from-aistudio.google.com"
python demo.py
```

Without a key, `demo.py` runs in `--mock` mode so you can see the shapes and flow
without any API calls.
