# Lesson 7 — Subagents: `AgentDefinition` + the `Agent` Tool

**File:** `lessons/07_subagents.py`
**Concept:** Delegating a narrow subtask to a separately-configured specialist agent
**Model:** main session `claude-haiku-4-5`; subagent `claude-haiku-4-5`
**Verified cost:** $0.0192 (final version)

## What this lesson is

A subagent is a self-contained agent configuration — its own system prompt, model,
and tool set — that the main agent can delegate a subtask to, invoked through the
built-in `Agent` tool. This lesson restricts the main session to *only* the `Agent`
tool, so every `tool_use` you see is unambiguously a delegation rather than the
main agent doing the work itself.

## Defining a subagent

```python
HAIKU_BOT = AgentDefinition(
    description="Writes a single haiku about a given topic. Use when the user wants a haiku.",
    prompt=(
        "You are a haiku-writing specialist. When given a topic, respond with "
        "exactly one haiku (5-7-5 syllables) and nothing else."
    ),
    model="claude-haiku-4-5",
    tools=[],
    background=False,
)
```

```python
options = ClaudeAgentOptions(
    tools=["Agent"],
    agents={"haiku-bot": HAIKU_BOT},
    permission_mode="bypassPermissions",
    model="claude-haiku-4-5",
)
```

Per the SDK's own docstring on `ClaudeAgentOptions.agents`: subagents are
"programmatically define[d]... invokable via the Agent tool." Keys are agent
names; values are `AgentDefinition` instances.

## Two findings from actually running it (not from the docs)

### 1. The main session's tool name and the CLI's internal registered name differ

`tools=["Agent"]` was set, and the `tool_use` block Claude emitted was literally
named `Agent`:

```
[tool_use] Agent({'subagent_type': 'haiku-bot', 'description': 'Write a haiku about recursion', ...})
```

But the raw `init` system message — the CLI's own startup handshake — reported:

```
'tools': ['Task']
```

Same underlying mechanism, two different names depending on which layer you're
looking at (model-facing vs. CLI-internal).

### 2. `AgentDefinition.background=False` had no observed effect

Subagents invoked via the `Agent` tool run as **background tasks** by default. The
first, unfiltered run of this script was extremely noisy — 80+ `thinking_tokens`
progress-ping system messages, plus a full two-turn stream: the main agent
continues *speculatively* while the subagent works in the background, then a
second turn picks up the real result once the background task finishes.

Setting `background=False` explicitly on `HAIKU_BOT` did **not** change this —
`task_started` still reported `is_backgrounded: True`. This is documented here as
an honest empirical finding for this SDK version (`0.2.152`), not an assumption.

Because of the background/two-turn behavior, this single `query()` call yields
**two `ResultMessage`s** with identical cost — not two separate charges, just two
turns within one call:

```
[text] I've launched the haiku-bot to write a haiku about recursion. It's working
in the background and I'll relay the output to you as soon as it completes.
[text] Stack grows ever deep
Functions call themselves again
Base case ends the chain
...
Here's the haiku about recursion from the haiku-bot:

Stack grows ever deep
Functions call themselves again
Base case ends the chain
[result] cost_usd=0.019183250000000002
[result] cost_usd=0.019183250000000002
```

## Filtering the noise

`SystemMessage` subtypes `"thinking_tokens"` (token-count progress pings) and
`"init"` (a large startup handshake dump) are filtered out of this script's output
as pure noise unrelated to delegation:

```python
elif isinstance(message, SystemMessage):
    if message.subtype not in ("thinking_tokens", "init"):
        print(f"[system:{message.subtype}] {message.data}")
```

What remains — `background_tasks_changed`, `task_started`, `task_updated`,
`task_notification` — is the actual subagent lifecycle: launched, running,
completed, with its result summary attached.

## `AgentDefinition` reference

| Field | Purpose |
|---|---|
| `description` | Shown to the main agent to decide when to delegate here |
| `prompt` | The subagent's own system prompt |
| `tools` / `disallowedTools` | The subagent's own tool restrictions |
| `model` | Alias (`"sonnet"`, `"opus"`, `"haiku"`, `"inherit"`) or full model ID |
| `skills`, `memory`, `mcpServers` | Additional scoped configuration |
| `background` | Intended to control background execution — did not take effect empirically in this version |
| `permissionMode`, `effort`, `maxTurns` | Per-subagent overrides of these same top-level concepts |

## Key takeaway

Subagents are genuinely isolated (own prompt, own model, own tools) but share the
same background-task infrastructure visible throughout Claude Code more broadly —
the exact machinery used for this conversation's own `Agent` tool calls. Expect a
two-turn stream and design your message handling to tolerate it, rather than
assuming a single flat response.

## Try it yourself

- Define a second subagent and have the main agent pick between them based on the
  task.
- Give the subagent a real tool (e.g. lesson 4's `roll_dice`) and observe whether
  its tool calls surface in the parent stream.
