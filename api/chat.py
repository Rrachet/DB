"""DB web chat: a Vercel serverless function.

POST /api/chat  with header  X-DB-Password: <DB_WEB_PASSWORD>
body: {"messages": [{"role": "user" | "assistant", "content": "..."}]}
returns: {"reply": "...", "provider": "gemini"}

Works with free AI keys (Gemini, Groq, OpenRouter) or Claude. See _providers.py.
Controlling your PC (apps, files, voice, screen) needs the Windows app.
"""

import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
import _providers  # noqa: E402

MAX_MESSAGES = 40
MAX_CHARS = 8000

_PERSONAS_FILE = os.path.join(os.path.dirname(__file__), "..", "shared", "personas.json")
with open(_PERSONAS_FILE, encoding="utf-8") as f:
    PERSONAS = json.load(f)

SYSTEM_PROMPT = """You are DB, a personal AI assistant, talking through the DB website.
Here you can chat and, when available, search the web. You can't control the user's computer
from the website; if they ask for that, tell them the DB Windows app can do it.
Keep replies short and clear.

PERSONALITY
{persona}"""


def system_prompt(name):
    p = PERSONAS.get(name) if isinstance(name, str) else None
    p = p or PERSONAS["jarvis"]
    lines = ["\n".join(p["style"]), "", "Examples of your voice (style only; the facts in them are made up):"]
    lines += [f"{'User' if r == 'user' else 'You'}: {t}" for r, t in p["examples"]]
    return SYSTEM_PROMPT.format(persona="\n".join(lines))


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
        if not _providers.available():
            return self._send(503, {"error": "The site owner hasn't added an AI key yet (e.g. GEMINI_API_KEY)."})
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
            text, provider = _providers.reply(system_prompt(data.get("persona")), messages)
            return self._send(200, {"reply": text, "provider": provider})
        except _providers.ProviderError as e:
            print(f"All providers failed: {e}", flush=True)  # shows in Vercel logs
            return self._send(502, {"error": "DB couldn't get an answer right now. Try again in a minute."})

    def do_GET(self):
        self._send(200, {"ok": True, "providers": _providers.available(), "personas": list(PERSONAS)})
