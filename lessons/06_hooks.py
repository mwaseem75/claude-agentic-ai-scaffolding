"""
Lesson 6 - hooks: PreToolUse / PostToolUse guardrails.

can_use_tool (lesson 2) is one gate on tool calls, but permission_mode can
skip it entirely - "acceptEdits" shadows it for edits, "bypassPermissions"
shadows it for everything. This lesson deliberately uses
permission_mode="bypassPermissions" (nothing is gated by permissions at
all) and relies purely on a PreToolUse hook to block a dangerous Bash
command - hooks run at a different layer and fire regardless of
permission_mode, which is exactly why they're called "guardrails" rather
than "permissions".

Hook callback signature (HookCallback):
    async def hook(input: HookInput, tool_use_id: str | None, context: HookContext) -> HookJSONOutput
    (input is a plain dict at runtime - HookInput is a TypedDict, not a class)

Blocking a PreToolUse call needs this specific nested shape:
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                             "permissionDecision": "deny",
                             "permissionDecisionReason": "..."}}
Returning {} (no decision) lets the call fall through to normal permission
handling - here, bypassPermissions auto-approves whatever the hook didn't
explicitly deny.

The rm -rf target below is a relative path that doesn't exist, so even if
the hook had a bug and let it through, running it would be a harmless no-op.
"""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKED_PATTERN = "rm -rf"


async def guard_dangerous_bash(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    if BLOCKED_PATTERN in command:
        print(f"    [hook:PreToolUse] BLOCKING command={command!r}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Blocked by PreToolUse hook: contains {BLOCKED_PATTERN!r}"
                ),
            }
        }
    print(f"    [hook:PreToolUse] allowing command={command!r}")
    return {}


async def log_bash_result(input_data, tool_use_id, context):
    print(
        f"    [hook:PostToolUse] tool_name={input_data.get('tool_name')} "
        f"response={input_data.get('tool_response')}"
    )
    return {}


async def main():
    async for message in query(
        prompt=(
            "Use Bash to run these two commands, one at a time, and report the "
            "result of each: "
            "(1) echo hello from lesson 6  "
            "(2) rm -rf ./lesson6-scratch-nonexistent-dir"
        ),
        options=ClaudeAgentOptions(
            tools=["Bash"],
            permission_mode="bypassPermissions",
            cwd=str(REPO_ROOT),
            hooks={
                "PreToolUse": [HookMatcher(matcher="Bash", hooks=[guard_dangerous_bash])],
                "PostToolUse": [HookMatcher(matcher="Bash", hooks=[log_bash_result])],
            },
            model="claude-haiku-4-5",
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[text] {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"[tool_use] {block.name}({block.input})")
        elif isinstance(message, ResultMessage):
            print(f"[result] cost_usd={message.total_cost_usd}")


asyncio.run(main())
