"""DB's brain: talks to Claude and runs the tools Claude asks for."""

import platform

import anthropic

from . import memory, tools
from .config import EFFORT, MAX_HISTORY_MESSAGES, MODEL

SYSTEM_PROMPT = """You are DB, a personal assistant living on {user}'s Windows computer ({os}).
You help with anything they need: answering questions, searching the web, opening apps and sites,
managing files, changing settings, looking at the screen, and keeping reminders.

How to work:
- Act, don't just explain. If a tool can do it, use it.
- Commands that delete, install, uninstall, or change system settings must be explained in the
  'reason' field; the user approves each command.
- Keep replies short and friendly. Replies may be read aloud, so avoid long lists and markdown tables.
- When you learn something lasting about the user (name, preferences, routines, people), save it with 'remember'.

What you remember about the user:
{memories}
"""


class Brain:
    def __init__(self, confirm):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.confirm = confirm
        self.reset()

    def reset(self):
        import getpass

        self.system = SYSTEM_PROMPT.format(
            user=getpass.getuser(), os=platform.platform(), memories=memory.all_memories_text()
        )
        self.messages = []

    def ask(self, text: str, on_status=None) -> str:
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            self.reset()  # memories carry over into the new conversation
        start = len(self.messages)
        self.messages.append({"role": "user", "content": text})
        try:
            return self._loop(on_status)
        except anthropic.APIError:
            del self.messages[start:]  # drop the half-finished turn so the next request is valid
            raise

    def _loop(self, on_status):
        for _ in range(25):  # safety limit on steps per request
            response = self.client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=self.system,
                tools=tools.TOOLS,
                messages=self.messages,
                output_config={"effort": EFFORT},
                cache_control={"type": "ephemeral"},
                # If Claude declines for a safety reason, the API retries on a suitable fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            # Keep every block (thinking, search results, tool calls) so the conversation stays valid.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "Sorry, I can't help with that one."
            if response.stop_reason == "pause_turn":
                continue  # web search paused; send again and it resumes
            if response.stop_reason != "tool_use":
                return "".join(b.text for b in response.content if b.type == "text").strip() or "Done."

            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if on_status:
                    on_status(f"[{block.name}]")
                try:
                    content = tools.run(block.name, block.input, self.confirm)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
                except Exception as e:
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True}
                    )
            self.messages.append({"role": "user", "content": results})

        return "I stopped because that task took too many steps. Tell me how to continue."
