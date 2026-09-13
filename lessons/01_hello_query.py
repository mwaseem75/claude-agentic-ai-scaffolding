"""
Lesson 1 — the query() loop and message types.

No tools here on purpose: agent.py already showed tool-use noise mixed in
with reasoning text. This lesson isolates the message shapes you'll see on
every query() call, with no built-in tools involved:

  - AssistantMessage -> content: list[TextBlock | ThinkingBlock | ToolUseBlock | ...]
      Even with tools=[] and no way to call anything, Claude can still emit
      a ThinkingBlock: its internal reasoning before writing the answer.
      That's a real, distinct block type - not noise - so we print it
      separately from the actual answer (TextBlock).
  - ResultMessage     -> the terminal "turn is over" message, with
                          cost/usage/timing info attached
"""

import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    query,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


async def main():
    async for message in query(
        prompt="In two sentences, what does 'agentic' mean for an LLM, "
        "as opposed to a plain chat completion?",
        options=ClaudeAgentOptions(
            tools=[],  # no built-in tools at all -> pure text response
            model="claude-haiku-4-5",  # cheapest tier - fine for this simple Q&A
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[text] {block.text}")
                elif isinstance(block, ThinkingBlock):
                    print(f"[thinking] {block.thinking}")
                else:
                    print(f"[other block] {type(block).__name__}")

        elif isinstance(message, ResultMessage):
            print(f"\n[result] subtype={message.subtype}")
            print(f"[result] turns={message.num_turns}  duration_ms={message.duration_ms}")
            print(f"[result] cost_usd={message.total_cost_usd}")


asyncio.run(main())
