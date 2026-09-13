# Lesson 5 — `ClaudeSDKClient`: Stateful, Multi-Turn Conversations

**File:** `lessons/05_stateful_client.py`
**Run it:** `uv run lessons/05_stateful_client.py`
**Concept:** Contrasting stateless `query()` against a persistent, multi-turn
`ClaudeSDKClient` connection
**Model:** `claude-haiku-4-5`
**Verified cost:** $0.008 total across 4 short calls

## What this lesson is

Every earlier lesson used `query()` — stateless, one-shot, with no memory between
calls. This lesson runs a direct, side-by-side comparison against
`ClaudeSDKClient`, which maintains a live, stateful connection across turns.

## Usage pattern

```python
async with ClaudeSDKClient(options=options) as client:
    await client.query("first message")
    async for message in client.receive_response():
        ...   # yields messages up to and including the ResultMessage
              # for THIS turn, then stops
    await client.query("follow-up")
    async for message in client.receive_response():
        ...
```

`receive_response()` differs from the lower-level `receive_messages()`: it
automatically terminates once it yields a `ResultMessage`, making it a clean
per-turn iterator instead of an endless stream.

## The experiment

Both demos send the exact same two prompts:

```python
TURN_1 = "My favorite number is 42. Just acknowledge that in a few words."
TURN_2 = "What's double my favorite number?"
```

**Demo A — `ClaudeSDKClient` (stateful, same connection):**
```python
async with ClaudeSDKClient(options=OPTIONS) as client:
    for turn_prompt in (TURN_1, TURN_2):
        await client.query(turn_prompt)
        async for message in client.receive_response():
            print_message(message)
```

**Demo B — `query()` × 2 (stateless, independent calls):**
```python
for turn_prompt in (TURN_1, TURN_2):
    async for message in query(prompt=turn_prompt, options=OPTIONS):
        print_message(message)
```

## Results

| | Turn 1 | Turn 2 ("What's double my favorite number?") |
|---|---|---|
| **`ClaudeSDKClient`** | *"Got it! 42 is a classic choice — the answer to everything, right?"* | **"Double your favorite number is 84."** — remembered the fact |
| **`query()` × 2** | *"Got it! 42 is a great choice—a classic number with cosmic significance."* | **"I don't have any information about what your favorite number is!"** — no shared history |

This is the clean, textbook contrast: `ClaudeSDKClient` keeps a live
session/connection so turns build on each other; `query()` starts completely fresh
every single call, no matter what was said moments before.

## `interrupt()` — mentioned, not exercised

`ClaudeSDKClient` also exposes `await client.interrupt()`, to cancel a turn that's
still generating (only meaningful in streaming mode, called from a separate
concurrent task while `receive_response()` is still iterating). This lesson
doesn't exercise it live: reliably interrupting a short, cheap response mid-stream
needs precise timing that's flaky in a short scripted demo. The call itself is
exactly what it looks like — no hidden complexity, just timing-sensitive to invoke
correctly.

## Reference

| Method | Purpose |
|---|---|
| `ClaudeSDKClient(options=...)` | Construct a client; use as `async with` (or manual `connect()`/`disconnect()`) |
| `await client.query(prompt, session_id="default")` | Send a message on the live connection |
| `async for msg in client.receive_response()` | Stream messages for the current turn, stopping after the `ResultMessage` |
| `async for msg in client.receive_messages()` | Stream messages indefinitely (no auto-stop) |
| `await client.interrupt()` | Cancel a still-generating turn |
| `await client.set_permission_mode(mode)` | Change permission mode mid-conversation |

## When to use which

| Use `query()` when... | Use `ClaudeSDKClient` when... |
|---|---|
| Simple one-off questions | Building a chat interface |
| Batch processing of independent prompts | Interactive, multi-turn conversations |
| Fire-and-forget automation scripts | You need to react to Claude's responses |
| All inputs are known upfront | You need interrupt capability |

## Key takeaway

Statefulness in this SDK is a *connection-level* property, not something `query()`
can be coaxed into. If a task needs memory across turns, reach for
`ClaudeSDKClient` from the start.

## Try it yourself

- Add a third turn to Demo A asking Claude to triple the number *from the first
  answer* (84 → 252), confirming memory compounds correctly.
- Try setting `session_id` explicitly on two different `client.query()` calls
  within the same client to see how separate sessions behave.
