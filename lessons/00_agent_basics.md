# Lesson 0 — The Basic Agent Loop

**File:** `agent.py` (repo root)
**Run it:** `uv run agent.py`
**Concept:** The `query()` agentic loop, `allowed_tools`, `permission_mode="acceptEdits"`
**Model:** default (unset)
**Cost:** not tracked (written before cost-tracking became a habit in later lessons)

## What this lesson is

This is the starting point of the whole curriculum — the first working script in the
repo, before the lesson series existed. Everything from Lesson 1 onward builds on the
pattern established here.

`agent.py` asks Claude to review `utils.py` for crash bugs and fix anything it finds,
using a restricted toolbox and hands-off permissions.

## The core mental model

Calling `query()` is not one API request-response pair. It is a **foreman handing a
contractor a job**: a prompt (the work order), a toolbox (`allowed_tools`), and a
policy for how much sign-off the contractor needs before acting
(`permission_mode`). The contractor then works autonomously — reading files,
thinking, editing, checking its own work — narrating each step as a stream of
`message` events, until it decides the job is done.

```python
async for message in query(
    prompt="Review utils.py for bugs that would cause crashes. Fix any issues you find.",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Glob"],  # the contractor's toolbox
        permission_mode="acceptEdits",            # don't ask before editing files
    ),
):
    ...
```

## Reading the message stream

Each `message` yielded by `query()` is a typed object. The two you see here:

- **`AssistantMessage`** — one turn of Claude "speaking." Its `.content` is a *list*
  of blocks, because in a single turn Claude can both narrate in plain text and
  invoke a tool:
  ```python
  if isinstance(message, AssistantMessage):
      for block in message.content:
          if hasattr(block, "text"):
              print(block.text)          # Claude's reasoning, in prose
          elif hasattr(block, "name"):
              print(f"Tool: {block.name}")  # a tool it just invoked
  ```
- **`ResultMessage`** — arrives exactly once, at the very end, marking the whole
  agentic loop as finished. `message.subtype` (e.g. `"success"`) tells you how it
  ended.

## Key configuration

| Field | Value here | What it does |
|---|---|---|
| `allowed_tools` | `["Read", "Edit", "Glob"]` | The only tools Claude may call, no matter what it decides it wants to do. No `Bash`, no `Write` — nothing outside this list is reachable. |
| `permission_mode` | `"acceptEdits"` | Auto-approves file-edit operations instead of pausing to ask. Without this, Claude would normally interrupt the loop to request approval before every edit. |

## A real bug this lesson taught us

The very first run of this script crashed with `UnicodeEncodeError: 'charmap' codec
can't encode character '→'`. Cause: on Windows, `print()` defaults to the
console's `cp1252` encoding, which can't represent characters like `→` that Claude's
output sometimes contains. The fix, added at the top of the script and copied into
*every* later lesson:

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")
```

Add this line first, before anything else touches stdout, in any Windows script that
prints Claude Agent SDK output.

## Where the tools actually live

`allowed_tools` names like `"Read"`, `"Edit"`, `"Glob"` are not Python functions
inside the `claude_agent_sdk` package — the package's `types.py` only declares them
as strings. The real implementations live in the **Claude Code CLI engine**. Under
the hood, `query()` locates and spawns the `claude` (or `claude.exe`) executable on
your `PATH` as a subprocess (see `_internal/transport/subprocess_cli.py`), and every
tool call you observe is that CLI process executing its own built-in tool — not code
running inside your `.venv`.

```
agent.py → claude_agent_sdk (Python) → spawns `claude` CLI as a subprocess
                                            ↑
                                  Read/Edit/Glob/Bash/... actually
                                  live and execute here
```

This is why the SDK requires Claude Code to be installed and reachable on `PATH` —
it's a thin, typed Python interface over the same engine as the interactive CLI.

## Try it yourself

- Change `allowed_tools` to `[]` and re-run — Claude can no longer read or edit
  anything; observe how its narration changes.
- Swap `permission_mode="acceptEdits"` for `"plan"` and see that the file is left
  untouched (this exact comparison is formalized in Lesson 2).
