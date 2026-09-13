# Claude Agentic AI Scaffolding

Nine small, working programs that teach you how the Claude Agent SDK actually
behaves — not by reading the docs, but by running things, watching them break,
and fixing them.

That's the honest pitch. Every lesson here is a runnable Python script under
30-100 lines, paired with a write-up that tells you exactly what happened when
it ran: the real output, the real cost in dollars, and — more than once — the
real bug I hit before I got it working.

If you've used ChatGPT-style chat completions and you're wondering what
"agentic" actually buys you beyond a longer system prompt, this repo answers
that question with code instead of slides.

## Agentic AI in one paragraph, and what these two repos actually cover

"Agentic" gets thrown around a lot, so here's the plain version. A normal LLM
call takes text in, gives text out, and stops there. An agent keeps going — it
decides which tool to call, looks at what came back, decides what to do next,
and repeats that loop by itself until the task is done or it needs your
sign-off to continue. That loop, plus everything wrapped around it — which
tools it's allowed to touch, who approves what, whether it remembers earlier
turns, what stops it from doing something destructive — is what "agentic AI
framework" means once you strip away the marketing. Everything else is
implementation detail.

This repo and its sibling, **[langchain-agentic-ai-scaffolding](https://github.com/mwaseem75/langchain-agentic-ai-scaffolding)**,
teach that scaffolding through the same nine ideas — once on the Claude Agent
SDK, once on LangChain — so you can tell which parts are universal and which
are just one framework's opinion:

1. **The agent loop itself** — what actually streams back when an agent runs, beyond a single response
2. **Permissions and approval gates** — who decides whether a risky action actually executes
3. **Identity and model choice** — giving the agent a persona, and what changes when you swap models
4. **Custom tools** — teaching the agent to do something it couldn't do on its own
5. **Statefulness** — the difference between an agent that remembers your last message and one that doesn't
6. **Guardrails that can't be switched off** — a safety rule that survives even a permissive configuration
7. **Delegating to a specialist** — one agent handing a subtask to another
8. **Talking to something external** — connecting a tool that runs in a completely separate process
9. **A capstone** — combining all of the above into one small agent that's actually safe to run unattended

Work through both repos back to back and you end up with a tested mental model
of agentic AI, not just familiarity with one framework's API surface.

## What the Claude Agent SDK actually is

A lot of people assume it's just another wrapper around the Claude API. It
isn't. `claude-agent-sdk` is a Python package that runs the *Claude Code CLI
engine* as a subprocess and gives you a typed interface to it. That distinction
matters more than it sounds:

```python
async for message in query(
    prompt="Review utils.py for bugs that would cause crashes. Fix any issues you find.",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Glob"],
        permission_mode="acceptEdits",
    ),
):
    ...
```

That's not a single API call. It's a foreman handing a contractor a job: a
prompt, a toolbox (`allowed_tools`), and a policy for how much sign-off it
needs before acting (`permission_mode`). The contractor — Claude Code, running
as a real subprocess on your machine — then works autonomously: reading files,
editing them, checking its own output, narrating every step as a stream of
typed messages, until it decides the job is done. Because it's built on Claude
Code, you get Read/Edit/Bash/Glob and friends for free. No other agent
framework I've used ships a working coding toolbox out of the box like that.

## Who this is for

You're comfortable with Python. You've probably called an LLM API before. You
haven't built anything *agentic* yet — tool loops, permission systems,
multi-turn state, guardrails — and you'd rather learn those concepts by
running real code than by reading a 40-page framework guide.

## Setup

```bash
uv sync
cp .env.example .env   # then paste in your real key
```

You need an Anthropic API key (get one at console.anthropic.com) and the
`claude` CLI itself installed and on your `PATH` — the SDK spawns it as a
subprocess, so if `claude` isn't discoverable, nothing here runs.

```bash
uv run lessons/01_hello_query.py
```

Every lesson runs the same way. Most default to `claude-haiku-4-5`
specifically so you can work through all nine without worrying about the
bill — the whole curriculum costs well under a dollar in API usage, and most
individual lessons cost less than a cent.

## The lessons

Each row is a script you run and a write-up that explains what it taught —
concept, annotated code, the actual output from running it, and a short
reference table.

| # | Run it | Read about it | What it actually teaches |
|---|--------|----------------|---------------------------|
| 0 | `agent.py` | [00_agent_basics.md](lessons/00_agent_basics.md) | The foreman/contractor loop, `allowed_tools`, hands-off permissions, and where Read/Edit/Bash actually live |
| 1 | `lessons/01_hello_query.py` | [01_hello_query.md](lessons/01_hello_query.md) | `query()`'s message stream isn't one response — it's text, thinking, and a result, even with zero tools |
| 2 | `lessons/02_tools_and_permissions.py` | [02_tools_and_permissions.md](lessons/02_tools_and_permissions.md) | Four permission modes, run side by side, and the exact moment your own permission callback gets silently skipped |
| 3 | `lessons/03_system_prompt_and_model.py` | [03_system_prompt_and_model.md](lessons/03_system_prompt_and_model.md) | Replacing vs. extending Claude's identity, and why effort barely moves the needle on easy questions |
| 4 | `lessons/04_custom_tools.py` | [04_custom_tools.md](lessons/04_custom_tools.md) | Giving Claude a capability it can't fake (real randomness) — and the naming bug that took a failed run to find |
| 5 | `lessons/05_stateful_client.py` | [05_stateful_client.md](lessons/05_stateful_client.md) | The exact line where "remembers your favorite number" turns into "has no idea what you're talking about" |
| 6 | `lessons/06_hooks.py` | [06_hooks.md](lessons/06_hooks.md) | A guardrail that survives even `bypassPermissions` — because it isn't a permission at all |
| 7 | `lessons/07_subagents.py` | [07_subagents.md](lessons/07_subagents.md) | Delegating to a specialist sub-agent, and the background-task machinery running underneath it |
| 8 | `lessons/08_mcp_external_server.py` | [08_mcp_external_server.md](lessons/08_mcp_external_server.md) | Proving a tool runs in a genuinely different OS process — by printing two different PIDs |
| 9 | `lessons/09_capstone.py` | [09_capstone.md](lessons/09_capstone.md) | "Repo Housekeeper" — a small agent that structurally *cannot* delete your files, with two independent safety layers |

## Three things I didn't expect to find

**A hook survives permission modes that were designed to skip everything.**
Lesson 6 sets `permission_mode="bypassPermissions"` — the mode that auto-approves
every single tool call, no questions asked — and then blocks a `rm -rf` command
anyway. Hooks and permissions turn out to be two completely separate layers,
and only one of them is worth using for a rule you never want silently disabled.

**The SDK's own example code was wrong about a real gotcha.** The docstring for
`create_sdk_mcp_server()` shows `allowed_tools=["roll_dice"]` — a bare tool
name. Following it literally gets you a permission denial on every call,
because the tool is actually invoked as `mcp__dice__roll_dice`. Lesson 4 walks
through the failed run and the fix, because "the docs told me to" is not a
great debugging strategy and I'd rather show you the failure than pretend it
didn't happen.

**Plan mode leaks its own guardrail text into the transcript.** Run Lesson 2
under `permission_mode="plan"` and Claude's response quotes the literal system
instruction it was given ("you MUST NOT make any edits..."). Small thing, but
it's a neat confirmation that `query()`'s plan mode isn't a separate
reimplementation — it's the exact same mechanism as the interactive CLI's.

## If you want the LangChain version too

There's a companion repo, **[langchain-agentic-ai-scaffolding](https://github.com/mwaseem75/langchain-agentic-ai-scaffolding)**,
covering the identical nine concepts rebuilt on LangChain's `create_agent`.
Same scenarios, same "Repo Housekeeper" capstone, different framework — a
useful way to see which parts of "agentic" are universal ideas and which
parts are just one SDK's opinion.

## License

MIT. Use this however is useful to you — fork it, strip it down, teach from
it, whatever.
