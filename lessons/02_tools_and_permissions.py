"""
Lesson 2 - allowed_tools, permission_mode, and the can_use_tool callback.

agent.py used permission_mode="acceptEdits" to silently skip permission
checks. This lesson makes the permission *system* itself visible: the same
task (edit utils.py, then verify it with a shell command) is run under four
different permission_mode values, with a can_use_tool callback that logs
every permission check the CLI actually asks it to make - and shows when a
permission_mode causes some tool calls to skip that callback entirely
("shadowing", per the SDK's own docstring on can_use_tool).

Permission mode primer:
  - "plan"              -> Claude may only plan; no tool actually executes.
  - "default"           -> tool calls needing approval go through can_use_tool.
  - "acceptEdits"       -> Edit/Write calls auto-approve, skipping can_use_tool.
                           Non-edit calls (like Bash) still go through it.
  - "bypassPermissions" -> everything auto-approves; can_use_tool is never
                           called at all (the SDK even warns about this).

`tools=[...]` controls what's *available* to call at all. Leaving
`allowed_tools` unset means nothing is force-auto-approved by that field -
approval instead comes from permission_mode + can_use_tool below.

`cwd` scopes where the agent's file/shell tools resolve relative paths from
- set explicitly here so this script works regardless of where it's run from.
"""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "utils.py"
ORIGINAL_CONTENT = TARGET.read_text(encoding="utf-8")

TASK = (
    "Use the Edit tool to add the single-line comment '# lesson-2-demo' as "
    "the very first line of utils.py. Then use Bash to run "
    "python -c \"print('checked')\" to confirm the file still parses. "
    "Report what happened in one sentence."
)


def make_can_use_tool(log: list[str]):
    """Build a fresh callback + log list for one demo run."""

    async def can_use_tool(tool_name, tool_input, context):
        log.append(tool_name)
        print(f"    [permission-check] tool={tool_name} input={tool_input}")
        if tool_name == "Bash":
            return PermissionResultDeny(message="Bash is blocked in this demo.")
        return PermissionResultAllow()

    return can_use_tool


async def run_demo(mode: str):
    print(f"\n=== permission_mode={mode!r} ===")
    TARGET.write_text(ORIGINAL_CONTENT, encoding="utf-8")  # identical starting state each time
    checks: list[str] = []

    async for message in query(
        prompt=TASK,
        options=ClaudeAgentOptions(
            tools=["Read", "Edit", "Bash"],
            permission_mode=mode,
            can_use_tool=make_can_use_tool(checks),
            cwd=str(REPO_ROOT),
            model="claude-haiku-4-5",
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"    [text] {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"    [tool_use] {block.name}({block.input})")
        elif isinstance(message, ResultMessage):
            print(f"    [result] subtype={message.subtype}  cost_usd={message.total_cost_usd}")

    changed = TARGET.read_text(encoding="utf-8") != ORIGINAL_CONTENT
    print(f"    [summary] permission-checks-seen={checks or 'none'}  utils.py changed={changed}")


async def main():
    for mode in ["plan", "default", "acceptEdits", "bypassPermissions"]:
        await run_demo(mode)
    TARGET.write_text(ORIGINAL_CONTENT, encoding="utf-8")  # leave the repo clean
    print("\nutils.py restored to its original content.")


asyncio.run(main())
