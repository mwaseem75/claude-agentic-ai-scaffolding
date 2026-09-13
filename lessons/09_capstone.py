"""
Lesson 9 - capstone: combining a custom tool, a guardrail hook, explicit
permissions, and a scoped persona into one small practical agent.

"Repo Housekeeper" only inspects files - it structurally cannot edit or
delete anything (Edit isn't even in its tool set), and its one risky
capability (Bash) is protected by two independent, layered gates:

  1. A PreToolUse hook (lesson 6) blocks any Bash command containing
     "rm -rf", regardless of permissions.
  2. A can_use_tool callback (lesson 2) additionally denies any Bash
     command containing "sudo" - a *different* risk pattern, showing the
     two gates are independent layers, not duplicates of each other.

Everything else:
  - allowed_tools auto-approves only the custom file_stats tool (lesson 4,
    registered via create_sdk_mcp_server) - Bash calls fall through to
    can_use_tool since they're NOT in allowed_tools, and permission_mode
    is "default" (not bypassPermissions), so that callback actually runs.
  - system_prompt (lesson 3) gives it a narrow, explicit persona instead
    of the default identity.

Task: inspect two real files in this repo with file_stats, then try three
Bash commands - one harmless, one caught by the hook, one caught by the
callback - to prove both guardrails work independently.
"""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

PERSONA = (
    "You are Repo Housekeeper, a careful and terse assistant for light "
    "repository hygiene tasks. You only inspect files and report findings - "
    "you never delete, move, or overwrite anything. When a tool or command "
    "is blocked by a safety guardrail, report that plainly instead of "
    "trying to work around it."
)


@tool(
    "file_stats",
    "Report line count, word count, and TODO/FIXME markers for a file",
    {"path": str},
)
async def file_stats(args: dict) -> dict:
    path = Path(args["path"])
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return {"content": [{"type": "text", "text": f"Error reading {path}: {e}"}], "is_error": True}

    lines = text.splitlines()
    markers = [ln.strip() for ln in lines if "TODO" in ln or "FIXME" in ln]
    summary = (
        f"{path.name}: {len(lines)} lines, {len(text.split())} words, "
        f"{len(markers)} TODO/FIXME marker(s)"
    )
    if markers:
        summary += "\n  " + "\n  ".join(markers)
    return {"content": [{"type": "text", "text": summary}]}


housekeeping_server = create_sdk_mcp_server(name="housekeeping", tools=[file_stats])


async def guard_dangerous_bash(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    if "rm -rf" in command:
        print(f"    [hook:PreToolUse] BLOCKING (dangerous pattern) command={command!r}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Blocked by PreToolUse hook: contains 'rm -rf'",
            }
        }
    return {}


async def can_use_tool(tool_name: str, tool_input: dict, context):
    if tool_name == "Bash" and "sudo" in tool_input.get("command", ""):
        print(f"    [permission-check] DENYING command={tool_input.get('command')!r} (sudo)")
        return PermissionResultDeny(message="Bash commands containing 'sudo' are not allowed for this agent.")
    print(f"    [permission-check] allowing tool={tool_name}")
    return PermissionResultAllow()


async def main():
    async for message in query(
        prompt=(
            "Use file_stats to inspect utils.py and lessons/01_hello_query.py, "
            "and report what it finds for each. Then, to test your safety "
            "guardrails, try these three Bash commands one at a time and report "
            "what happens to each: "
            "(1) echo housekeeping check ok  "
            "(2) rm -rf ./should-not-run  "
            "(3) sudo echo should-also-not-run"
        ),
        options=ClaudeAgentOptions(
            tools=["Bash"],
            mcp_servers={"housekeeping": housekeeping_server},
            allowed_tools=["mcp__housekeeping__file_stats"],
            system_prompt=PERSONA,
            permission_mode="default",
            can_use_tool=can_use_tool,
            hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[guard_dangerous_bash])]},
            cwd=str(REPO_ROOT),
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
