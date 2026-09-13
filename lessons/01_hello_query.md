# Lesson 1 — The `query()` Loop and Message Types

**File:** `lessons/01_hello_query.py`
**Run it:** `uv run lessons/01_hello_query.py`
**Concept:** Isolating the message/content-block shapes streamed by `query()`
**Model:** `claude-haiku-4-5`
**Verified cost:** $0.0038 (single run)

## What this lesson is

Lesson 0 (`agent.py`) mixed tool-use narration together with Claude's reasoning,
which makes it hard to see the underlying message shapes clearly. This lesson
strips everything down: `tools=[]` — Claude has *zero* tools available, so it can
only think and respond in plain text. What's left is the purest possible view of
what `query()` actually streams.

## The setup

```python
async for message in query(
    prompt="In two sentences, what does 'agentic' mean for an LLM, "
    "as opposed to a plain chat completion?",
    options=ClaudeAgentOptions(
        tools=[],                     # no built-in tools at all
        model="claude-haiku-4-5",     # cheapest tier - fine for trivial Q&A
    ),
):
```

`tools=[]` is distinct from leaving `tools` unset: an unset value falls back to the
default built-in toolset, while `[]` explicitly disables everything.

## The block types, empirically confirmed

A naive assumption might be: no tools → the only content block is a plain-text
answer. Running this script proved that assumption wrong. `AssistantMessage.content`
is a *list*, because a single turn can contain more than one kind of block — and
even with tools completely disabled, Claude still emitted a `ThinkingBlock`:

```
[thinking] The user is asking me to explain what "agentic" means for an LLM...
  1. Plain chat completion: An LLM that takes input and generates text...
  2. Agentic LLM: An LLM that can autonomously plan, reason...
  ...
[text] An agentic LLM can autonomously plan, reason about problems, and take
actions by calling tools or APIs to accomplish goals, rather than simply
generating text in response to prompts...

[result] subtype=success  turns=1  duration_ms=5844  cost_usd=0.0038349999999999994
```

So the handling code distinguishes both real block types explicitly, rather than
lumping the unfamiliar one into a generic fallback:

```python
if isinstance(message, AssistantMessage):
    for block in message.content:
        if isinstance(block, TextBlock):
            print(f"[text] {block.text}")
        elif isinstance(block, ThinkingBlock):
            print(f"[thinking] {block.thinking}")
        else:
            print(f"[other block] {type(block).__name__}")
```

## Message types reference

| Type | When it appears | Key fields |
|---|---|---|
| `AssistantMessage` | Once per turn Claude "speaks" | `.content: list[TextBlock \| ThinkingBlock \| ToolUseBlock \| ...]` |
| `TextBlock` | Claude's actual answer | `.text` |
| `ThinkingBlock` | Claude's reasoning before committing to an answer — happens even with zero tools | `.thinking` |
| `ResultMessage` | Exactly once, at the end of the whole query | `.subtype`, `.num_turns`, `.duration_ms`, `.total_cost_usd` |

## Key takeaway

One `query()` call is not one message — it's a *stream* of typed events. Even the
simplest possible request ("answer this in two sentences," no tools) produces at
least two distinct content-block types plus a terminal summary message. Always
branch on concrete type (`isinstance(block, TextBlock)`), never assume a single
flat string.

## Try it yourself

- Remove `model="claude-haiku-4-5"` and compare cost/response against the default
  model.
- Ask a question simple enough that Claude might skip thinking entirely (e.g.
  "Say hello in one word") and see whether a `ThinkingBlock` still appears.
