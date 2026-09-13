"""
Lesson 5 - ClaudeSDKClient: stateful, multi-turn conversations.

Every earlier lesson used query() - stateless, one-shot, no memory between
calls. This lesson contrasts that directly against ClaudeSDKClient:

  - Demo A (ClaudeSDKClient): tell it a fact, then ask a follow-up question
    that depends on remembering that fact, across two separate
    client.query() calls on the SAME connection.
  - Demo B (query(), for contrast): the exact same two prompts, but each
    sent via its own independent query() call. Since query() is stateless,
    the second call has no idea what the first call was told.

Usage pattern (per client.py's own __aenter__/__aexit__):
    async with ClaudeSDKClient(options=...) as client:
        await client.query("first message")
        async for message in client.receive_response():
            ...   # receive_response() yields messages up to and including
                  # the ResultMessage for THIS turn, then stops - unlike
                  # receive_messages(), which never stops on its own.
        await client.query("follow-up")
        async for message in client.receive_response():
            ...

Note on interrupt(): ClaudeSDKClient also supports client.interrupt() to
cancel a turn that's still generating (only meaningful in streaming mode,
mid-response). This lesson doesn't exercise it live - reliably interrupting
a short, cheap Haiku response mid-stream needs precise timing that's flaky
in a short scripted demo - but the call is exactly that: `await
client.interrupt()` from another concurrent task while receive_response()
is still iterating.
"""

import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    query,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

TURN_1 = "My favorite number is 42. Just acknowledge that in a few words."
TURN_2 = "What's double my favorite number?"

OPTIONS = ClaudeAgentOptions(tools=[], model="claude-haiku-4-5")


def print_message(message):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(f"  [text] {block.text}")
    elif isinstance(message, ResultMessage):
        print(f"  [result] cost_usd={message.total_cost_usd}")


async def demo_stateful_client():
    print("=== Demo A: ClaudeSDKClient (stateful, same connection) ===")
    async with ClaudeSDKClient(options=OPTIONS) as client:
        for turn_prompt in (TURN_1, TURN_2):
            print(f"> {turn_prompt}")
            await client.query(turn_prompt)
            async for message in client.receive_response():
                print_message(message)


async def demo_stateless_query():
    print("\n=== Demo B: query() x2 (stateless, independent calls) ===")
    for turn_prompt in (TURN_1, TURN_2):
        print(f"> {turn_prompt}")
        async for message in query(prompt=turn_prompt, options=OPTIONS):
            print_message(message)


async def main():
    await demo_stateful_client()
    await demo_stateless_query()


asyncio.run(main())
