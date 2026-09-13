# Lesson 8 — External MCP Servers (stdio) vs. In-Process Tools

**File:** `lessons/08_mcp_external_server.py` + `lessons/_mcp_word_count_server.py`
**Concept:** Wiring a genuinely separate OS process as a tool provider, contrasted
with Lesson 4's in-process server
**Model:** `claude-haiku-4-5`
**Verified cost:** $0.031 (worked on the first run)

## What this lesson is

Lesson 4's `create_sdk_mcp_server` ran a custom tool inside the *same* Python
process as the calling script. The SDK also supports three ways to reach a tool
provider running somewhere else entirely:

```python
{"type": "stdio", "command": "...", "args": [...], "env": {...}}   # separate OS process
{"type": "sse",   "url": "...", "headers": {...}}                   # remote, Server-Sent Events
{"type": "http",  "url": "...", "headers": {...}}                   # remote, streamable HTTP
```

This lesson uses `"stdio"` against a tiny standalone server script — no network,
no external installs required.

## The external server

`lessons/_mcp_word_count_server.py` is a **separate script**, run directly as its
own process, not imported:

```python
from mcp.server.mcpserver import MCPServer

server = MCPServer(name="wordcount")

@server.tool()
def count_words(text: str) -> str:
    count = len(text.split())
    return f"{count} words (counted in external process pid={os.getpid()})"

if __name__ == "__main__":
    server.run()   # default transport="stdio"
```

**Version gotcha, caught by actually importing it:** many MCP tutorials reference
`from mcp.server.fastmcp import FastMCP`. In the installed `mcp` 2.x package, that
module raises `ModuleNotFoundError` on import with an explicit migration message —
`FastMCP` was renamed to `mcp.server.mcpserver.MCPServer`. Check your installed
`mcp` package version before copying older examples.

## Wiring it up as an external process

```python
SERVER_SCRIPT = Path(__file__).resolve().parent / "_mcp_word_count_server.py"

options = ClaudeAgentOptions(
    mcp_servers={
        "wordcount": {
            "type": "stdio",
            "command": sys.executable,      # this venv's python.exe
            "args": [str(SERVER_SCRIPT)],
        }
    },
    allowed_tools=["mcp__wordcount__count_words"],   # server-prefixed, per lesson 4
    permission_mode="bypassPermissions",
    model="claude-haiku-4-5",
)
```

`sys.executable` is used so the SDK spawns the exact same virtual environment's
interpreter — no separate install or `uv run` re-invocation needed.

## Proving it's really a different process

The lesson script prints its own PID at startup, and the tool reports its own PID
when called:

```
[lesson script] my own pid=596
...
Word count: 9 words
Process info: The counting was performed in an external process with PID 39552
```

**596 vs. 39552** — two genuinely separate OS processes communicating over stdio.
Contrast with Lesson 4, where the tool's `call_log` list (defined in the calling
script) was mutated directly by the tool and read back afterward — only possible
because that tool ran in the *same* process.

## In-process vs. external — when to use which

| | In-process (Lesson 4) | External stdio (this lesson) |
|---|---|---|
| Performance | No IPC overhead | Subprocess + stdio serialization overhead |
| State access | Direct access to your app's Python objects | None — communicates only via tool call/result |
| Isolation | Shares your process's crashes, memory, dependencies | Crashes independently; can use a different language/runtime entirely |
| Deployment | Simplest — one process | Requires managing a second process's lifecycle |
| Best for | Tools tightly coupled to your app's own state | Reusable tools, tools in another language, sandboxing risky operations |

## Reference

| Config type | Shape | Use case |
|---|---|---|
| `McpStdioServerConfig` | `{"type": "stdio", "command": str, "args": [str], "env": {str: str}}` | Local subprocess |
| `McpSSEServerConfig` | `{"type": "sse", "url": str, "headers": {str: str}}` | Remote, Server-Sent Events |
| `McpHttpServerConfig` | `{"type": "http", "url": str, "headers": {str: str}}` | Remote, streamable HTTP |
| `McpSdkServerConfig` | Produced by `create_sdk_mcp_server()` | In-process (Lesson 4) |

## Key takeaway

The choice between in-process and external MCP servers is a real architectural
decision, not just a config detail — it determines whether a tool can touch your
application's live state directly, and whether its failures are isolated from your
main process.

## Try it yourself

- Add a second tool to `_mcp_word_count_server.py` and confirm both appear under
  the same `mcp__wordcount__` prefix.
- Point `command`/`args` at a real external MCP server binary (if you have Node.js
  installed, an `npx`-based server works the same way) instead of the local Python
  script.
