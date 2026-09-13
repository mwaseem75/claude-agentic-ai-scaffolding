"""
Standalone external MCP server for Lesson 8.

Run directly (not imported) - this executes as a SEPARATE OS process from
08_mcp_external_server.py, launched over stdio by the SDK's
McpStdioServerConfig. Contrast with lesson 4's create_sdk_mcp_server, which
runs tools inside the SAME process as the calling script.

Version-tolerant import: the `mcp` package's server class was renamed
between major versions - `mcp.server.fastmcp.FastMCP` (mcp 1.x) became
`mcp.server.mcpserver.MCPServer` (mcp 2.x). This file tries the 2.x import
first and falls back to the 1.x one, so it works regardless of which
major version of `mcp` ends up installed as a transitive dependency.
"""

import os

try:
    from mcp.server.mcpserver import MCPServer  # mcp >= 2.0
except ModuleNotFoundError:
    from mcp.server.fastmcp import FastMCP as MCPServer  # mcp < 2.0

server = MCPServer(name="wordcount")


@server.tool()
def count_words(text: str) -> str:
    """Count the words in `text` and report which OS process did the counting."""
    count = len(text.split())
    return f"{count} words (counted in external process pid={os.getpid()})"


if __name__ == "__main__":
    server.run()
