"""Jarvis and Ultron personalities, and which one is active."""

import json
from pathlib import Path

from .config import DATA_DIR

PERSONAS = json.loads((Path(__file__).resolve().parent.parent / "shared" / "personas.json").read_text(encoding="utf-8"))
DEFAULT = "jarvis"
_SETTINGS = DATA_DIR / "settings.json"


def _settings():
    try:
        return json.loads(_SETTINGS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def current() -> str:
    name = _settings().get("persona", DEFAULT)
    return name if name in PERSONAS else DEFAULT


def set_current(name: str) -> str:
    name = name.strip().lower()
    if name not in PERSONAS:
        return f"Unknown mode '{name}'. Options: {', '.join(PERSONAS)}."
    s = _settings()
    s["persona"] = name
    _SETTINGS.write_text(json.dumps(s, indent=2), encoding="utf-8")
    return f"Switched to {PERSONAS[name]['title']} mode. It takes effect from your next message."


def prompt(name: str) -> str:
    p = PERSONAS[name]
    lines = ["\n".join(p["style"]), "", "Examples of your voice (style only; the facts in them are made up):"]
    for role, text in p["examples"]:
        lines.append(f"{'User' if role == 'user' else 'You'}: {text}")
    return "\n".join(lines)
