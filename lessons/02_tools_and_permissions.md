# Lesson 2 — `allowed_tools`, `permission_mode`, and `can_use_tool`

**File:** `lessons/02_tools_and_permissions.py`
**Run it:** `uv run lessons/02_tools_and_permissions.py`
**Concept:** How the SDK's permission system actually gates tool calls, and when
your own gate (`can_use_tool`) gets silently skipped ("shadowed")
**Model:** `claude-haiku-4-5`
**Verified cost:** $0.0408 total across 4 runs

## What this lesson is

Lesson 0 used `permission_mode="acceptEdits"` to silently skip permission checks.
This lesson makes the permission *system itself* visible by running the identical
task under four different `permission_mode` values, with a `can_use_tool` callback
that logs every permission check the CLI actually consults it for.

## The task

Every run attempts the same two actions on a freshly-reset `utils.py`:
1. Use `Edit` to add a one-line comment as the first line of the file.
2. Use `Bash` to run `python -c "print('checked')"` to verify it still parses.

```python
TASK = (
    "Use the Edit tool to add the single-line comment '# lesson-2-demo' as "
    "the very first line of utils.py. Then use Bash to run "
    "python -c \"print('checked')\" to confirm the file still parses. "
    "Report what happened in one sentence."
)
```

`utils.py` is reset to its original content before each of the four runs (and
restored again at the very end), so every mode starts from identical state.

## `tools` vs. `allowed_tools`

These two `ClaudeAgentOptions` fields are easy to conflate:

- **`tools`** — what's *available to call at all*. `tools=["Read", "Edit", "Bash"]`
  means Claude cannot reach for anything outside this list, full stop.
- **`allowed_tools`** — what's *force-auto-approved*, bypassing the permission gate
  entirely. This lesson leaves it unset, so nothing skips the gate by this
  mechanism — approval instead comes purely from `permission_mode` +
  `can_use_tool` below.

## The `can_use_tool` callback

```python
async def can_use_tool(tool_name, tool_input, context):
    log.append(tool_name)
    print(f"    [permission-check] tool={tool_name} input={tool_input}")
    if tool_name == "Bash":
        return PermissionResultDeny(message="Bash is blocked in this demo.")
    return PermissionResultAllow()
```

Signature: `Callable[[str, dict, ToolPermissionContext], Awaitable[PermissionResult]]`
— this is the SDK's programmatic replacement for the interactive "Allow this
tool call? y/n" prompt you'd see in the terminal.

## Results — verified by actually running each mode

| `permission_mode` | `can_use_tool` invoked for | `utils.py` changed? | What happened |
|---|---|---|---|
| `"plan"` | *(never — no tools execute at all)* | No | Claude refused to touch anything; its own response quoted the real plan-mode guardrail text ("you MUST NOT make any edits...") |
| `"default"` | `Edit`, `Bash` | Yes | Both calls went through the callback — `Edit` allowed, `Bash` denied |
| `"acceptEdits"` | `Bash` only | Yes | **`Edit` never reached the callback** — auto-approved silently by the mode itself; `Bash` (not an edit-type call) still got gated and denied |
| `"bypassPermissions"` | *(never)* | Yes | Everything auto-approved; the SDK printed a `CanUseToolShadowedWarning` at startup warning that the callback is pointless in this mode |

The clearest result is `"acceptEdits"`. Claude's own summary confirmed the
shadowing directly:

> *"I successfully added the comment '# lesson-2-demo' as the first line of
> utils.py using the Edit tool, but the Bash tool is blocked in this demo
> environment, so I was unable to run the Python parse verification command."*

## Permission mode reference

| Mode | Behavior |
|---|---|
| `"plan"` | Claude may only plan; no tool actually executes |
| `"default"` | Tool calls needing approval go through `can_use_tool` |
| `"acceptEdits"` | `Edit`/`Write` calls auto-approve, skipping `can_use_tool`. Everything else still gets gated |
| `"bypassPermissions"` | Everything auto-approves; `can_use_tool` is never consulted at all |

## Key takeaway

`can_use_tool` is not an unconditional gate — it's the *fallback* path for calls the
CLI's own rules would otherwise "ask" about. A permissive `permission_mode` can
silently bypass it entirely for some or all tools ("shadowing"), and the SDK will
warn you about this at startup if it detects the combination. If you need a gate
that **cannot** be shadowed regardless of `permission_mode`, that's what hooks are
for — see Lesson 6.

## Try it yourself

- Add `"Read"` to `allowed_tools` and see the `CanUseToolShadowedWarning` fire even
  under `"default"` mode.
- Change the callback to deny `Edit` too, and observe how Claude adapts its final
  summary when every action is blocked.
