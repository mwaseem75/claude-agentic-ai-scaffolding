"""
Lesson 8 - external MCP servers: stdio/SSE/HTTP config, contrasted with
lesson 4's in-process create_sdk_mcp_server.

Three external config shapes exist (McpStdioServerConfig, McpSSEServerConfig,
McpHttpServerConfig), alongside the in-process McpSdkServerConfig from
lesson 4:

  {"type": "stdio", "command": "...", "args": [...], "env": {...}}  -> spawns
      a separate OS process, talks MCP over its stdin/stdout
  {"type": "sse", "url": "...", "headers": {...}}                    -> a
      remote server reached over Server-Sent Events
  {"type": "http", "url": "...", "headers": {...}}                   -> a
      remote server reached over streamable HTTP

This lesson uses "stdio" against a tiny standalone server script
(_mcp_word_count_server.py), launched as its own OS process - no network,
no external installs (no npx-based server was needed for this). That
tool reports its own os.getpid() so you can see, concretely, that it runs
in a genuinely different process than this script - unlike lesson 4's
in-process tool, which shared this exact process and could touch this
script's own Python variables directly.
"""

import asyncio
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

SERVER_SCRIPT = Path(__file__).resolve().parent / "_mcp_word_count_server.py"

print(f"[lesson script] my own pid={os.getpid()}")


async def main():
    async for message in query(
        prompt=(
            "Use the count_words tool to count the words in this sentence: "
            "'The quick brown fox jumps over the lazy dog.' "
            "Report the count and any process info it gives you."
        ),
        options=ClaudeAgentOptions(
            mcp_servers={
                "wordcount": {
                    "type": "stdio",
                    "command": sys.executable,
                    "args": [str(SERVER_SCRIPT)],
                }
            },
            allowed_tools=["mcp__wordcount__count_words"],
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
        elif isinstance(message, ResultMessage):
            print(f"[result] cost_usd={message.total_cost_usd}")


asyncio.run(main())
