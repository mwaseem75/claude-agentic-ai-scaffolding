"""
Lesson 4 - custom tools: @tool + create_sdk_mcp_server.

Every built-in tool so far (Read/Edit/Bash/Glob) ships with the CLI. This
lesson gives Claude a brand-new capability that exists only in *this*
Python process: an in-process MCP server exposing a `roll_dice` tool that
calls Python's real random.randint() - something an LLM cannot do reliably
on its own (language models are not good, true random-number generators).

The SDK's own docstring for create_sdk_mcp_server() shows allowed_tools
using the tool's bare name (e.g. "roll_dice"). That's misleading in
practice: running this once with allowed_tools=["roll_dice"] showed Claude
actually calling it as "mcp__dice__roll_dice" (server-name-prefixed) and
getting denied every time, since the bare name never matched. allowed_tools
below uses the real prefixed name - "mcp__<server_name>__<tool_name>" -
confirmed by printing the raw tool_use block name, not by trusting the docs.

Tool results come back as a ToolResultBlock inside a *UserMessage* (not the
AssistantMessage) - the transcript echoes them as if the tool "replied" as
the user turn. That's why this script handles UserMessage too.
"""

import asyncio
import random
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

call_log: list[str] = []  # direct access to this process's own state from inside the tool


@tool("roll_dice", "Roll an n-sided die and return the actual result", {"sides": int})
async def roll_dice(args: dict) -> dict:
    sides = args["sides"]
    result = random.randint(1, sides)
    call_log.append(f"rolled d{sides} -> {result}")
    return {"content": [{"type": "text", "text": f"Rolled a d{sides}: {result}"}]}


dice_server = create_sdk_mcp_server(name="dice", version="1.0.0", tools=[roll_dice])


async def main():
    async for message in query(
        prompt=(
            "Roll two 6-sided dice using the roll_dice tool (one call per die), "
            "then tell me their sum and whether it's even or odd."
        ),
        options=ClaudeAgentOptions(
            mcp_servers={"dice": dice_server},
            allowed_tools=["mcp__dice__roll_dice"],
            model="claude-haiku-4-5",
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[text] {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"[tool_use] name={block.name!r} input={block.input}")
        elif isinstance(message, UserMessage):
            for block in message.content if isinstance(message.content, list) else []:
                if isinstance(block, ToolResultBlock):
                    print(f"[tool_result] {block.content}")
        elif isinstance(message, ResultMessage):
            print(f"[result] cost_usd={message.total_cost_usd}")

    print(f"\n[in-process call_log] {call_log}")


asyncio.run(main())
