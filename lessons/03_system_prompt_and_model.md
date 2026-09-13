# Lesson 3 — `system_prompt`, `model`, and `effort`

**File:** `lessons/03_system_prompt_and_model.py`
**Concept:** The three shapes of `system_prompt`, and controlling thinking depth
via `effort`
**Model:** `claude-haiku-4-5` (demos 1–3), `claude-sonnet-5` (demos 4–5)
**Verified cost:** $0.018 total across 5 runs

## What this lesson is

Every earlier lesson ran with no `system_prompt` at all — which means Claude
answers as a bare model with **no assigned identity**, not the full "Claude Code"
persona you get from the interactive CLI. This lesson demonstrates all three
`system_prompt` shapes, side by side, plus the `effort` knob for controlling
thinking depth.

## The three `system_prompt` shapes

```python
# 1. None (the default used in every prior lesson) — no identity at all
options = ClaudeAgentOptions(system_prompt=None, ...)

# 2. A plain string — REPLACES the identity entirely
CUSTOM_PERSONA = (
    "You are Ruthless Reviewer, a terse senior code-review bot. "
    "Speak only in short, blunt statements. Never use filler pleasantries."
)
options = ClaudeAgentOptions(system_prompt=CUSTOM_PERSONA, ...)

# 3. The built-in preset, EXTENDED with your own instruction
PRESET_WITH_APPEND = {
    "type": "preset",
    "preset": "claude_code",
    "append": "Always end every response with the exact tag [CUSTOM-PERSONA].",
}
options = ClaudeAgentOptions(system_prompt=PRESET_WITH_APPEND, ...)
```

## Results — the same prompt, three different identities

Prompt: *"In one sentence, introduce yourself and describe your role for me."*

| `system_prompt` | Response |
|---|---|
| `None` | *"I'm Claude, an AI agent built on Anthropic's Claude Agent SDK, here to help you accomplish tasks..."* — generic, SDK-aware, but no Claude Code identity |
| Custom string | *"I'm Ruthless Reviewer—I tear apart your code and tell you what's wrong with it, no sugar-coating."* — identity and tone completely replaced |
| Preset + `append` | *"I'm Claude Code, Anthropic's CLI assistant for software engineering tasks—I help you write, debug, refactor, and understand code in your project."* **followed by `[CUSTOM-PERSONA]`** on its own line |

This is the key distinction: a plain string **replaces** the system prompt
entirely; the preset + `append` form **extends** the built-in Claude Code identity
without discarding it.

## `effort`

```python
await run_demo(
    "effort='low'", REASON_TASK,
    system_prompt=CUSTOM_PERSONA, model="claude-sonnet-5", effort="low",
)
await run_demo(
    "effort='high'", REASON_TASK,
    system_prompt=CUSTOM_PERSONA, model="claude-sonnet-5", effort="high",
)
```

Valid values: `"low" | "medium" | "high" | "xhigh" | "max"`.

**Important gotcha, confirmed by actually hitting it:** `claude-haiku-4-5` does not
accept `effort` — it only supports adaptive thinking with no depth control. The
effort demos in this lesson deliberately switch to `claude-sonnet-5`, one of the
smallest models that supports the full range.

Result on the trivial question "Is 17 a prime number?": both `effort="low"` and
`effort="high"` answered correctly at nearly identical cost ($0.0021 each), and
neither produced a visible `ThinkingBlock`. This is a real, useful finding — not a
bug: `effort` mostly matters on genuinely hard problems. On a trivial fact lookup,
adaptive thinking doesn't engage differently regardless of the effort ceiling.

## Reference

| Field | Type | Notes |
|---|---|---|
| `system_prompt` | `str \| {"type": "preset", "preset": "claude_code", "append": str?} \| {"type": "file", "path": str} \| None` | `None` = no identity; string = full replacement; preset = built-in identity, optionally extended |
| `model` | `str \| None` | Model alias or full ID |
| `effort` | `"low" \| "medium" \| "high" \| "xhigh" \| "max" \| None` | Rejected by `claude-haiku-4-5`; supported on Sonnet 5 and above |

## Key takeaway

With `system_prompt=None` — the default every earlier lesson used — Claude does
**not** know it's "Claude Code." It only knows it's running via the Agent SDK. If
you want the full built-in coding-assistant identity, you must opt in explicitly
via the `claude_code` preset.

## Try it yourself

- Try `system_prompt={"type": "file", "path": "..."}` pointing at a `.md` file with
  a persona written out.
- Ask a genuinely hard reasoning question at `effort="low"` vs `effort="max"` and
  compare both the `ThinkingBlock` length and the final answer quality.
