"""Free AI providers for the Windows app (Gemini, Groq, OpenRouter) plus Claude.

All three free providers speak the same "OpenAI-compatible" format, so one
loop handles tool use for all of them. See README for how to get free keys.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 60

DEFAULT_ORDER = ["gemini", "groq", "openrouter", "claude"]
KEY_NAMES = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}

# OpenAI-compatible endpoints and their default free models.
OPENAI_STYLE = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_MODEL", "gemini-2.5-flash"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_MODEL", "openai/gpt-oss-120b"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_MODEL", "openrouter/free"),
}


class LLMError(Exception):
    pass


def available():
    order = [p.strip().lower() for p in os.environ.get("DB_PROVIDERS", "").split(",") if p.strip()]
    order = order or DEFAULT_ORDER
    return [p for p in order if p in KEY_NAMES and os.environ.get(KEY_NAMES[p])]


def post_json(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise LLMError(f"connection failed: {e}") from None


def chat(provider, messages, tools):
    """One OpenAI-style chat call. Returns the assistant message dict."""
    base, model_env, default_model = OPENAI_STYLE[provider]
    body = {"model": os.environ.get(model_env, default_model), "messages": messages}
    if tools:
        body["tools"] = tools
    headers = {"Authorization": f"Bearer {os.environ[KEY_NAMES[provider]]}"}
    if provider == "openrouter":
        headers["X-Title"] = "DB Assistant"
    data = post_json(f"{base}/chat/completions", body, headers)
    try:
        return data["choices"][0]["message"]
    except (KeyError, IndexError):
        raise LLMError(f"{provider} gave no answer: {json.dumps(data)[:300]}") from None


def google_search(query: str) -> str:
    """Answer a question using Gemini with Google Search (free tier includes a daily allowance)."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return (
            "Web search needs a free GEMINI_API_KEY. Instead, you can open a Google search for the user "
            f"with open_url: https://www.google.com/search?q={urllib.parse.quote(query)}"
        )
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": f"Search the web and answer with key facts and sources: {query}"}]}],
        "tools": [{"google_search": {}}],
    }
    data = post_json(url, body, {"x-goog-api-key": key})
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise LLMError(f"search gave no answer: {json.dumps(data)[:300]}") from None
    return "".join(p.get("text", "") for p in parts).strip() or "No results."

