# Lesson 6 — Hooks: `PreToolUse` / `PostToolUse` Guardrails

**File:** `lessons/06_hooks.py`
**Run it:** `uv run lessons/06_hooks.py`
**Concept:** A safety gate that operates independently of the permission system
**Model:** `claude-haiku-4-5`
**Verified cost:** $0.0135 (worked on the first run)

## What this lesson is

Lesson 2 showed that `can_use_tool` can be silently **shadowed** — `acceptEdits`
skips it for edits, `bypassPermissions` skips it for everything. This lesson
deliberately uses `permission_mode="bypassPermissions"` (nothing is gated by
permissions at all) and relies purely on a `PreToolUse` hook to block a dangerous
`Bash` command. Hooks run at a different layer and fire **regardless** of
`permission_mode` — that's exactly why they're the right tool for a guardrail that
must never be silently skipped.

## Hook callback signature

```python
async def hook(
    input: HookInput,          # a plain dict at runtime, not a class instance
    tool_use_id: str | None,
    context: HookContext,
) -> HookJSONOutput:
    ...
```

Registered via:

```python
hooks={
    "PreToolUse": [HookMatcher(matcher="Bash", hooks=[guard_dangerous_bash])],
    "PostToolUse": [HookMatcher(matcher="Bash", hooks=[log_bash_result])],
}
```

`matcher` narrows which tool names trigger the hook (`"Bash"`, or e.g.
`"Write|Edit"` to match either). Matchers registered on the same event dispatch
concurrently, not sequentially.

## Blocking a call from `PreToolUse`

```python
async def guard_dangerous_bash(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    if BLOCKED_PATTERN in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Blocked by PreToolUse hook: contains {BLOCKED_PATTERN!r}",
            }
        }
    return {}   # no decision -> falls through to normal permission handling
```

Returning `{}` is not "deny by omission" — it means *no opinion*, and the call
proceeds through whatever `permission_mode` would otherwise decide (here,
`bypassPermissions` auto-approves it).

## Results

```
    [hook:PreToolUse] allowing command='echo hello from lesson 6'
    [hook:PostToolUse] tool_name=Bash response={'stdout': 'hello from lesson 6', ...}

    [hook:PreToolUse] BLOCKING command='rm -rf ./lesson6-scratch-nonexistent-dir'
```

- The harmless `echo` command passed the hook, actually ran, and `PostToolUse`
  logged its real stdout.
- The `rm -rf` command was **denied before it ever ran** — there's no
  `PostToolUse` log line for it at all, confirming it never executed.
- Claude's own summary correctly reported the denial: *"blocked by a safety
  hook... requires explicit authorization to run."*

The target path (`./lesson6-scratch-nonexistent-dir`) doesn't exist, so even if the
hook logic had a bug and let the command through, running it would have been a
harmless no-op — a deliberate safety margin for a demo script.

## `HookJSONOutput` reference (the fields that matter here)

| Field | Purpose |
|---|---|
| `hookSpecificOutput.hookEventName` | Must match the firing event, e.g. `"PreToolUse"` |
| `hookSpecificOutput.permissionDecision` | `"allow" \| "deny" \| "ask" \| "defer"` |
| `hookSpecificOutput.permissionDecisionReason` | Shown to Claude / logged, explaining the decision |
| `decision` (top-level) | `"block"` — a simpler stop signal for non-`PreToolUse` events |

## Key takeaway

Permission modes and hooks are two independent layers. A permissive
`permission_mode` (even `bypassPermissions`) cannot bypass a hook's explicit deny —
hooks are the right place for a rule that must hold no matter how permissions are
configured elsewhere.

## Try it yourself

- Broaden `BLOCKED_PATTERN` to a list of dangerous substrings (`"rm -rf"`,
  `"format c:"`, `del /f`) and test each.
- Add a `PostToolUse` hook that rewrites `tool_response` via
  `updatedToolOutput` before Claude sees it.
