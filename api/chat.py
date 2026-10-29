"""DB web chat: a Vercel serverless function.

POST /api/chat  with header  X-DB-Password: <DB_WEB_PASSWORD>
body: {"messages": [{"role": "user" | "assistant", "content": "..."}]}
returns: {"reply": "..."}

The web version can chat and search the web. Controlling your PC
(apps, files, voice, screen) needs the Windows app.
"""

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler

import anthropic

MODEL = os.environ.get("DB_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("DB_EFFORT", "medium")
MAX_MESSAGES = 40
MAX_CHARS = 8000

SYSTEM_PROMPT = """You are DB, a friendly personal assistant, talking through the DB website.
Here you can chat and search the web. You can't control the user's computer from the website;
if they ask for that, tell them the DB Windows app can do it.
Keep replies short and clear."""


def _clean(messages):
    """Accept only plain text turns that alternate user/assistant and end with the user."""
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    messages = messages[-MAX_MESSAGES:]
    while messages and messages[0].get("role") != "user":
        messages = messages[1:]
    out = []
    for m in messages:
        role, content = m.get("role"), m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            raise ValueError("each message needs a role (user/assistant) and text content")
        if out and out[-1]["role"] == role:
            raise ValueError("messages must alternate between user and assistant")
        out.append({"role": role, "content": content[:MAX_CHARS]})
    if not out or out[-1]["role"] != "user":
        raise ValueError("the last message must be from the user")
    return out


def _reply(messages):
    client = anthropic.Anthropic()
    for _ in range(5):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
            messages=messages,
            output_config={"effort": EFFORT},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "pause_turn":  # web search paused; resend to resume
            messages = messages + [{"role": "assistant", "content": response.content}]
            continue
        if response.stop_reason == "refusal":
            return "Sorry, I can't help with that one."
        return "".join(b.text for b in response.content if b.type == "text").strip() or "Done."
    return "That search took too long. Please try again."


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        password = os.environ.get("DB_WEB_PASSWORD", "")
        if not password:
            return self._send(503, {"error": "The site owner hasn't set DB_WEB_PASSWORD yet."})
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return self._send(503, {"error": "The site owner hasn't set ANTHROPIC_API_KEY yet."})
        given = self.headers.get("X-DB-Password", "")
        if not hmac.compare_digest(given.encode(), password.encode()):
            return self._send(401, {"error": "Wrong password."})

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 400_000:
                return self._send(413, {"error": "Conversation too long. Start a new chat."})
            data = json.loads(self.rfile.read(length) or b"{}")
            messages = _clean(data.get("messages"))
        except (ValueError, AttributeError) as e:
            return self._send(400, {"error": str(e)})

        try:
            return self._send(200, {"reply": _reply(messages)})
        except anthropic.RateLimitError:
            return self._send(429, {"error": "DB is busy. Try again in a minute."})
        except anthropic.APIError as e:
            return self._send(502, {"error": f"Claude API error: {getattr(e, 'message', str(e))}"})

    def do_GET(self):
        self._send(200, {"ok": True, "model": MODEL})
