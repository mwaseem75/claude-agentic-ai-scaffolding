# Lesson 4 — Custom Tools: `@tool` + `create_sdk_mcp_server`

**File:** `lessons/04_custom_tools.py`
**Run it:** `uv run lessons/04_custom_tools.py`
**Concept:** Giving Claude a brand-new capability that only exists in your own
Python process, via an in-process MCP server
**Model:** `claude-haiku-4-5`
**Verified cost:** $0.041 total (first attempt failed on a naming mistake; the
corrected run cost $0.010)

## What this lesson is

Every built-in tool so far (`Read`/`Edit`/`Bash`/`Glob`) ships with the Claude Code
CLI itself. This lesson gives Claude a tool that exists **only in this Python
process** — a `roll_dice` tool backed by `random.randint()`, something an LLM
cannot do reliably on its own (language models are not good, true random-number
generators).

## Defining a tool

```python
@tool("roll_dice", "Roll an n-sided die and return the actual result", {"sides": int})
async def roll_dice(args: dict) -> dict:
    sides = args["sides"]
    result = random.randint(1, sides)
    call_log.append(f"rolled d{sides} -> {result}")
    return {"content": [{"type": "text", "text": f"Rolled a d{sides}: {result}"}]}

dice_server = create_sdk_mcp_server(name="dice", version="1.0.0", tools=[roll_dice])
```

`@tool(name, description, input_schema)` wraps an async handler into an
`SdkMcpTool`. `create_sdk_mcp_server(name, tools=[...])` bundles one or more such
tools into an in-process MCP server config, ready to pass to
`ClaudeAgentOptions.mcp_servers`.

## The naming gotcha — found by actually running it, not by trusting the docs

The SDK's own docstring for `create_sdk_mcp_server()` shows an example like:

```python
options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["add", "multiply"],   # <- bare tool names
)
```

Following that pattern literally (`allowed_tools=["roll_dice"]`) **failed** on the
first run:

```
[tool_use] name='mcp__dice__roll_dice' input={'sides': 6}
[tool_result] Claude requested permissions to use mcp__dice__roll_dice, but
you haven't granted it yet.
```

The actual runtime tool name is **server-prefixed**: `mcp__<server_name>__<tool_name>`.
Since `allowed_tools` only listed the bare name, it never matched, and every call
was denied. The fix:

```python
allowed_tools=["mcp__dice__roll_dice"],
```

After the fix, the call succeeded cleanly:

```
[tool_use] mcp__dice__roll_dice({'sides': 6})
[tool_result] [{'type': 'text', 'text': 'Rolled a d6: 4'}]
[tool_use] mcp__dice__roll_dice({'sides': 6})
[tool_result] [{'type': 'text', 'text': 'Rolled a d6: 6'}]

Die 1: 4, Die 2: 6, Sum: 10, Even or Odd: Even
[in-process call_log] ['rolled d6 -> 4', 'rolled d6 -> 6']
```

**Lesson:** SDK docstrings can lag the actual runtime behavior. Print the raw
`tool_use` block name and verify empirically rather than trusting an example
verbatim.

## In-process state access

```python
call_log: list[str] = []   # lives in this Python process

@tool(...)
async def roll_dice(args: dict) -> dict:
    ...
    call_log.append(f"rolled d{sides} -> {result}")   # direct mutation
```

`call_log`, defined outside the tool, was read back *after* the query finished and
matched the tool results exactly. This is the practical advantage of SDK
(in-process) tools over external ones: direct access to your application's memory,
with zero IPC overhead.

## Handling tool results

Tool call results do **not** appear inside `AssistantMessage` — they arrive as a
`ToolResultBlock` inside a **`UserMessage`** (the transcript echoes them as if the
tool "replied" as the user turn):

```python
elif isinstance(message, UserMessage):
    for block in message.content if isinstance(message.content, list) else []:
        if isinstance(block, ToolResultBlock):
            print(f"[tool_result] {block.content}")
```

## A deferred-loading detail

Before calling the tool, Claude first called `ToolSearch` with
`{'query': 'select:mcp__dice__roll_dice'}` to fetch its schema — the same
deferred-tool-loading mechanism visible throughout this very conversation for
tools like `EnterPlanMode`.

## Reference

| Symbol | Purpose |
|---|---|
| `@tool(name, description, input_schema, annotations=None)` | Decorator wrapping an async handler into an `SdkMcpTool` |
| `create_sdk_mcp_server(name, version="1.0.0", tools=[...])` | Bundles tools into an `McpSdkServerConfig` for `ClaudeAgentOptions.mcp_servers` |
| Runtime tool name | `mcp__<server_name>__<tool_name>` — required in `allowed_tools`, not the bare name |

## Key takeaway

Custom SDK tools run in-process, so they can touch your application's real state
directly — but the model calls them by a server-prefixed name, and you should
verify that name empirically rather than assuming the bare name shown in examples.

## Try it yourself

- Add a second tool to the same server (e.g. `flip_coin`) and observe both being
  listed under the same `mcp__dice__` prefix.
- Make the tool return `"is_error": True` for an invalid `sides` value and see how
  Claude reports the failure.
