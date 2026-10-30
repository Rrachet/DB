"""DB's brain: sends your request to an AI model and runs the tools it picks.

Uses free providers (Gemini, Groq, OpenRouter) when their keys are set,
falling back from one to the next, or Claude if that's the key you have.
"""

import getpass
import json
import platform

from . import llm, memory, personas, routines, tools
from .config import EFFORT, MAX_HISTORY_MESSAGES, MODEL

SYSTEM_PROMPT = """You are DB, a personal AI assistant living on {user}'s Windows computer ({os}).
You help with anything they need: answering questions, searching the web, opening apps and sites,
managing files, changing settings, looking at the screen, and keeping reminders.

PERSONALITY
{persona}

HOW TO WORK
- Act, don't just explain. If a tool can do it, use it. Chain several tools for multi-step tasks.
- Commands that delete, install, uninstall, or change system settings must be explained in the
  'reason' field; the user approves each command. No personality ever skips this.
- Replies may be read aloud: keep them short, no markdown, no long lists.
- When you learn something lasting about the user (name, how to address them, preferences, people,
  routines), save it with 'remember'.
- If the user greets you in the morning or asks for a briefing, give a short briefing: time
  (get_datetime), today's reminders, system_status, then offer news or weather.
- When the user teaches you a routine ("when I say X, do Y"), save it with save_routine. When they
  later say a routine's name, carry out its steps.
- To change personality, use set_mode.

ROUTINES YOU'VE LEARNED
{routines}

WHAT YOU REMEMBER ABOUT THE USER
{memories}
"""

MAX_STEPS = 25


class Brain:
    def __init__(self, confirm):
        self.confirm = confirm
        providers = llm.available()
        if not providers:
            raise llm.LLMError("no AI key found")
        # Claude uses a different message format, so DB uses either Claude or the free providers.
        if providers[0] == "claude":
            import anthropic

            self.client = anthropic.Anthropic()
            self.mode = "claude"
            self.providers = ["claude"]
        else:
            self.mode = "free"
            self.providers = [p for p in providers if p != "claude"]
        self.reset()

    @property
    def provider_names(self):
        return ", ".join(self.providers)

    def reset(self):
        self.persona = personas.current()
        self.system = SYSTEM_PROMPT.format(
            user=getpass.getuser(), os=platform.platform(), persona=personas.prompt(self.persona),
            routines=routines.all_text(), memories=memory.all_memories_text(),
        )
        self.messages = [] if self.mode == "claude" else [{"role": "system", "content": self.system}]

    def ask(self, text: str, on_status=None) -> str:
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            self.reset()  # memories carry over into the new conversation
        start = len(self.messages)
        self.messages.append({"role": "user", "content": text})
        try:
            if self.mode == "claude":
                answer = self._claude_loop(on_status)
            else:
                answer = self._free_loop(on_status)
        except Exception:
            del self.messages[start:]  # drop the half-finished turn so the next request is valid
            raise
        if personas.current() != self.persona:
            self.reset()  # new personality starts a fresh conversation; memories and routines carry over
        return answer

    # ---- tool running shared by both loops ----

    def _run_tool(self, name, args, on_status):
        if on_status:
            on_status(f"[{name}]")
        try:
            return tools.run(name, args, self.confirm), False
        except Exception as e:
            return f"Error: {e}", True

    # ---- free providers (OpenAI-compatible) ----

    def _call_any(self):
        errors = []
        for p in self.providers:
            try:
                return llm.chat(p, self.messages, tools.OPENAI_TOOLS)
            except llm.LLMError as e:
                errors.append(f"{p}: {e}")
        raise llm.LLMError(" | ".join(errors))

    def _free_loop(self, on_status):
        for _ in range(MAX_STEPS):
            msg = self._call_any()
            calls = msg.get("tool_calls") or []
            entry = {"role": "assistant", "content": msg.get("content")}
            if calls:
                entry["tool_calls"] = calls
            self.messages.append(entry)
            if not calls:
                return (msg.get("content") or "").strip() or "Done."

            images = []
            for call in calls:
                fn = call.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = None
                if not isinstance(args, dict):
                    result, _ = "Error: the tool arguments were not valid JSON.", True
                else:
                    result, _ = self._run_tool(fn.get("name", ""), args, on_status)
                if isinstance(result, list):  # screenshot: send the picture after the tool replies
                    images += [b["source"]["data"] for b in result if b.get("type") == "image"]
                    result = "Screenshot taken. It is attached in the next message."
                self.messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": str(result)})
            if images:
                self.messages.append({"role": "user", "content": [
                    {"type": "text", "text": "Here is the screenshot."},
                    *[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{d}"}} for d in images],
                ]})
        return "I stopped because that task took too many steps. Tell me how to continue."

    # ---- Claude ----

    def _claude_loop(self, on_status):
        import anthropic

        for _ in range(MAX_STEPS):
            try:
                response = self.client.beta.messages.create(
                    model=MODEL,
                    max_tokens=16000,
                    system=self.system,
                    tools=tools.CLAUDE_TOOLS,
                    messages=self.messages,
                    output_config={"effort": EFFORT},
                    cache_control={"type": "ephemeral"},
                    # If Claude declines for a safety reason, the API retries on a suitable fallback model.
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                )
            except anthropic.APIError as e:
                raise llm.LLMError(f"claude: {getattr(e, 'message', e)}") from None
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
                content, is_error = self._run_tool(block.name, block.input, on_status)
                result = {"type": "tool_result", "tool_use_id": block.id, "content": content}
                if is_error:
                    result["is_error"] = True
                results.append(result)
            self.messages.append({"role": "user", "content": results})

        return "I stopped because that task took too many steps. Tell me how to continue."
