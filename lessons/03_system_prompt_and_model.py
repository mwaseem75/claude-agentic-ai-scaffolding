"""
Lesson 3 - system_prompt, model, and effort.

Every earlier lesson let the SDK run with no system_prompt at all, which
means Claude answers as a bare model with no assigned identity - NOT the
full "Claude Code" persona you get in the interactive CLI. This lesson
shows all three system_prompt shapes plus the effort knob:

  1. system_prompt=None                              -> no identity at all
  2. system_prompt="<custom string>"                  -> your own persona,
                                                          replacing everything
  3. system_prompt={"type": "preset", "preset":
     "claude_code", "append": "..."}                  -> keep Claude Code's
                                                          built-in identity,
                                                          add one instruction
  4/5. effort="low" vs effort="high"                   -> same persona, same
                                                          question, different
                                                          thinking depth

Model note: `effort` is rejected by claude-haiku-4-5 (it only accepts
adaptive thinking with no effort control), so the effort demos switch to
claude-sonnet-5 - still cheap for a one-line question, and one of the
smallest models that actually supports the full low..max effort range.
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

INTRO_TASK = "In one sentence, introduce yourself and describe your role for me."
REASON_TASK = "Is 17 a prime number? Answer with just yes or no and a one-sentence reason."

CUSTOM_PERSONA = (
    "You are Ruthless Reviewer, a terse senior code-review bot. "
    "Speak only in short, blunt statements. Never use filler pleasantries "
    "like 'I'd be happy to' or 'Great question'."
)

PRESET_WITH_APPEND = {
    "type": "preset",
    "preset": "claude_code",
    "append": "Always end every response with the exact tag [CUSTOM-PERSONA].",
}


async def run_demo(label: str, prompt: str, **option_kwargs):
    print(f"\n=== {label} ===")
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(tools=[], **option_kwargs),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"  [text] {block.text}")
                elif isinstance(block, ThinkingBlock):
                    print(f"  [thinking, {len(block.thinking)} chars] {block.thinking[:120]}...")
        elif isinstance(message, ResultMessage):
            print(f"  [result] cost_usd={message.total_cost_usd}")


async def main():
    await run_demo(
        "1. system_prompt=None (no identity)",
        INTRO_TASK,
        model="claude-haiku-4-5",
    )
    await run_demo(
        "2. custom string system_prompt",
        INTRO_TASK,
        system_prompt=CUSTOM_PERSONA,
        model="claude-haiku-4-5",
    )
    await run_demo(
        "3. preset system_prompt + append",
        INTRO_TASK,
        system_prompt=PRESET_WITH_APPEND,
        model="claude-haiku-4-5",
    )
    await run_demo(
        "4. custom persona, effort='low'",
        REASON_TASK,
        system_prompt=CUSTOM_PERSONA,
        model="claude-sonnet-5",
        effort="low",
    )
    await run_demo(
        "5. custom persona, effort='high'",
        REASON_TASK,
        system_prompt=CUSTOM_PERSONA,
        model="claude-sonnet-5",
        effort="high",
    )


asyncio.run(main())
