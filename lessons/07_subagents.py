"""
Lesson 7 - subagents: AgentDefinition + ClaudeAgentOptions.agents.

A subagent is a separate, specialized agent configuration (its own prompt,
model, tools) that the main agent can delegate a subtask to. Per the SDK's
own docstring on ClaudeAgentOptions.agents: subagents are "invokable via
the Agent tool" - so the main session needs "Agent" in its tool set to
delegate at all.

This lesson restricts the main session to ONLY the Agent tool (tools=
["Agent"]) so every tool_use you see is unambiguously a delegation, not the
main agent doing the work itself. The subagent ("haiku-bot") is a narrow
specialist: one job, its own system prompt, its own (cheap) model, no tools
of its own since writing a haiku needs no file/shell access.

permission_mode="bypassPermissions" is used here purely to keep the demo
free of unrelated permission-check noise - the interesting part of this
lesson is delegation, not permissions (already covered in lesson 2).

The first run (without filtering) was very noisy, and confirmed something
worth knowing: subagents invoked via the Agent tool run as background
tasks (task_started reports is_backgrounded=True) *regardless* of
AgentDefinition.background=False below - the main agent continues
speculatively while the subagent works, then a second turn (with its own
ResultMessage) picks up the real result once the background task
completes. That's why two [result] lines print below with identical cost -
this is one query() call spanning two turns, not two separate queries.
SystemMessage 'thinking_tokens' pings (token-count progress ticks) and the
large 'init' dump are filtered out below as noise unrelated to delegation.

One genuine finding from that noisy first run, worth keeping: the raw
'init' system message reported the built-in tool as 'tools': ['Task'],
even though ClaudeAgentOptions.tools=["Agent"] was set and the tool_use
block Claude actually emitted was named 'Agent'. The CLI's internal
registered name and the name exposed to the model aren't the same string.
"""

import asyncio
import sys

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

HAIKU_BOT = AgentDefinition(
    description="Writes a single haiku about a given topic. Use when the user wants a haiku.",
    prompt=(
        "You are a haiku-writing specialist. When given a topic, respond with "
        "exactly one haiku (5-7-5 syllables) and nothing else - no preamble, "
        "no explanation."
    ),
    model="claude-haiku-4-5",
    tools=[],
    background=False,
)


async def main():
    async for message in query(
        prompt=(
            "Use the haiku-bot subagent to write a haiku about recursion. "
            "Relay its output back to me verbatim."
        ),
        options=ClaudeAgentOptions(
            tools=["Agent"],
            agents={"haiku-bot": HAIKU_BOT},
            permission_mode="bypassPermissions",
            model="claude-haiku-4-5",
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[text] {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"[tool_use] {block.name}({block.input})")
        elif isinstance(message, SystemMessage):
            if message.subtype not in ("thinking_tokens", "init"):
                print(f"[system:{message.subtype}] {message.data}")
        elif isinstance(message, ResultMessage):
            print(f"[result] cost_usd={message.total_cost_usd}")


asyncio.run(main())
