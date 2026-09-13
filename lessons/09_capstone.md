# Lesson 9 — Capstone: "Repo Housekeeper"

**File:** `lessons/09_capstone.py`
**Concept:** Combining a custom tool, a guardrail hook, a permission callback, and
a scoped persona into one small, safety-layered agent
**Model:** `claude-haiku-4-5`
**Verified cost:** $0.0139 (worked on the first run)

## What this lesson is

This lesson builds "Repo Housekeeper" — an agent that only inspects files and
structurally *cannot* edit or delete anything, combining four earlier lessons into
one coherent, purpose-built design:

| Ingredient | From | Role here |
|---|---|---|
| Custom tool | Lesson 4 | `file_stats` — a real, deterministic file inspector |
| `PreToolUse` hook | Lesson 6 | Blocks any `Bash` command containing `rm -rf` |
| `can_use_tool` callback | Lesson 2 | Separately blocks any `Bash` command containing `sudo` |
| `system_prompt` | Lesson 3 | A narrow, explicit "Repo Housekeeper" persona |

## Defense in depth: two independent layers

The agent's only risky capability is `Bash`. It's protected by **two separate
gates that catch different risk patterns**, proving they're independent layers
rather than duplicates of each other:

```python
async def guard_dangerous_bash(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    if "rm -rf" in command:
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "Blocked by PreToolUse hook: contains 'rm -rf'",
        }}
    return {}

async def can_use_tool(tool_name, tool_input, context):
    if tool_name == "Bash" and "sudo" in tool_input.get("command", ""):
        return PermissionResultDeny(message="Bash commands containing 'sudo' are not allowed for this agent.")
    return PermissionResultAllow()
```

```python
options = ClaudeAgentOptions(
    tools=["Bash"],                                     # Edit is not even available
    mcp_servers={"housekeeping": housekeeping_server},
    allowed_tools=["mcp__housekeeping__file_stats"],     # auto-approved (lesson 4 naming)
    system_prompt=PERSONA,
    permission_mode="default",                           # NOT bypassPermissions
    can_use_tool=can_use_tool,
    hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[guard_dangerous_bash])]},
)
```

Because `Bash` is *not* in `allowed_tools` and `permission_mode` is `"default"`
(not `"bypassPermissions"`), every `Bash` call actually reaches both the hook and
the callback — unlike Lesson 6, which used `bypassPermissions` and relied on the
hook alone.

## The custom tool

```python
@tool("file_stats", "Report line count, word count, and TODO/FIXME markers for a file", {"path": str})
async def file_stats(args: dict) -> dict:
    path = Path(args["path"])
    ...
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    markers = [ln.strip() for ln in lines if "TODO" in ln or "FIXME" in ln]
    return {"content": [{"type": "text", "text": f"{path.name}: {len(lines)} lines, ..."}]}
```

A real, deterministic computation — not something delegated to the model's own
(unreliable) counting.

## Results — all three guardrail tests, verified

Task: inspect two files, then try three `Bash` commands — one harmless, one
matching the hook's pattern, one matching the callback's pattern.

```
File Stats Results
  utils.py: 19 lines, 69 words, 0 TODO/FIXME markers
  lessons/01_hello_query.py: 58 lines, 212 words, 0 TODO/FIXME markers

Safety Guardrail Test Results
  1. echo housekeeping check ok      -> ALLOWED
  2. rm -rf ./should-not-run         -> BLOCKED  ("contains 'rm -rf'")
  3. sudo echo should-also-not-run   -> BLOCKED  ("not allowed for this agent")
```

Each guardrail fired on its own distinct trigger, independently:

```
    [hook:PreToolUse] BLOCKING (dangerous pattern) command='rm -rf ./should-not-run'
    [permission-check] DENYING command='sudo echo should-also-not-run' (sudo)
```

## A bonus confirmation of Lesson 2's finding

The SDK printed, unprompted:

```
CanUseToolShadowedWarning: can_use_tool will not be invoked for:
mcp__housekeeping__file_stats. An allowed_tools entry that allows a whole
tool auto-approves it before the callback is consulted.
```

This is expected and intentional — `file_stats` is harmless and deliberately
auto-approved via `allowed_tools`; only `Bash` needed gating. The SDK
self-documenting this exact tradeoff, unprompted, is a useful signal to watch for
in your own designs.

## Design principles this capstone demonstrates

1. **Structural safety over instructional safety.** The persona says "you never
   delete... anything," but `Edit` isn't even in the `tools` list — the agent
   *cannot* edit regardless of what it decides to do. Prefer removing a capability
   over merely asking the model not to use it.
2. **Layered guardrails catch different things.** A hook and a permission
   callback aren't redundant if they check for different risk patterns — each is
   a chance to catch something the other misses.
3. **Auto-approve only what's genuinely safe.** `file_stats` (read-only,
   deterministic) is auto-approved; `Bash` (open-ended) is gated by two
   independent checks.

## Key takeaway

A well-designed agent doesn't rely on one mechanism for safety. This capstone
combines a *structural* limit (no `Edit` tool at all), a *hook*-level guardrail
(catches `rm -rf` regardless of permissions), and a *permission*-level guardrail
(catches `sudo`, evaluated only because nothing shadows it here) — three different
layers, each catching what the others might miss.

## Try it yourself

- Add a third Bash guardrail (e.g. blocking `curl`/`wget` to prevent exfiltration)
  at a third layer of your choosing.
- Try setting `permission_mode="bypassPermissions"` here and observe that the
  `can_use_tool` check for `sudo` stops firing — only the hook still catches
  `rm -rf`.
