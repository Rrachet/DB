"""AI providers for the DB website. Free ones first, Claude last.

DB uses every provider that has a key set, in this order, and moves to the
next one if a provider fails or hits its free limit:

    GEMINI_API_KEY      Google Gemini (free key: https://aistudio.google.com/apikey), has Google Search
    GROQ_API_KEY        Groq (free key: https://console.groq.com/keys)
    OPENROUTER_API_KEY  OpenRouter free models (free key: https://openrouter.ai/keys)
    ANTHROPIC_API_KEY   Claude (paid)

Set DB_PROVIDERS=groq,gemini (for example) to change the order or limit the list.
Model names can be changed with GEMINI_MODEL, GROQ_MODEL, OPENROUTER_MODEL, DB_MODEL.
"""

import json
import os
import urllib.error
import urllib.request

TIMEOUT = 40

DEFAULT_ORDER = ["gemini", "groq", "openrouter", "claude"]
KEY_NAMES = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


class ProviderError(Exception):
    pass


def available():
    order = [p.strip().lower() for p in os.environ.get("DB_PROVIDERS", "").split(",") if p.strip()]
    order = order or DEFAULT_ORDER
    return [p for p in order if p in KEY_NAMES and os.environ.get(KEY_NAMES[p])]


def _post(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise ProviderError(f"HTTP {e.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ProviderError(f"connection failed: {e}") from None


def _gemini(system, messages):
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
        "tools": [{"google_search": {}}],
    }
    data = _post(url, body, {"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise ProviderError(f"no answer from Gemini: {json.dumps(data)[:300]}") from None
    return "".join(p.get("text", "") for p in parts).strip()


def _openai_compatible(base_url, key_env, model, system, messages, extra_headers=None):
    body = {"model": model, "messages": [{"role": "system", "content": system}, *messages]}
    headers = {"Authorization": f"Bearer {os.environ[key_env]}", **(extra_headers or {})}
    data = _post(f"{base_url}/chat/completions", body, headers)
    try:
        return (data["choices"][0]["message"].get("content") or "").strip()
    except (KeyError, IndexError):
        raise ProviderError(f"no answer: {json.dumps(data)[:300]}") from None


def _groq(system, messages):
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    return _openai_compatible("https://api.groq.com/openai/v1", "GROQ_API_KEY", model, system, messages)


def _openrouter(system, messages):
    model = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
    return _openai_compatible(
        "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", model, system, messages,
        {"X-Title": "DB Assistant"},
    )


def _claude(system, messages):
    import anthropic

    client = anthropic.Anthropic()
    msgs = list(messages)
    try:
        for _ in range(5):
            response = client.beta.messages.create(
                model=os.environ.get("DB_MODEL", "claude-opus-5-5"),
                max_tokens=16000,
                system=system,
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
                messages=msgs,
                output_config={"effort": os.environ.get("DB_EFFORT", "medium")},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if response.stop_reason == "pause_turn":  # web search paused; resend to resume
                msgs = msgs + [{"role": "assistant", "content": response.content}]
                continue
            if response.stop_reason == "refusal":
                return "Sorry, I can't help with that one."
            return "".join(b.text for b in response.content if b.type == "text").strip()
    except anthropic.APIError as e:
        raise ProviderError(getattr(e, "message", str(e))) from None
    raise ProviderError("web search took too many steps")


CALLS = {"gemini": _gemini, "groq": _groq, "openrouter": _openrouter, "claude": _claude}


def reply(system, messages):
    """Return (answer, provider_used). Tries each provider with a key until one works."""
    providers = available()
    if not providers:
        raise ProviderError("no AI key is set")
    errors = []
    for p in providers:
        try:
            text = CALLS[p](system, messages)
            if text:
                return text, p
            errors.append(f"{p}: empty answer")
        except ProviderError as e:
            errors.append(f"{p}: {e}")
    raise ProviderError(" | ".join(errors))
