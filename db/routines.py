"""Routines: commands you teach DB, like "work mode" = open VS Code, Spotify and Slack."""

import json
import threading

from .config import DATA_DIR

ROUTINES_FILE = DATA_DIR / "routines.json"
_lock = threading.Lock()


def _load():
    try:
        return json.loads(ROUTINES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(items):
    ROUTINES_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def save(name: str, steps: str) -> str:
    key = name.strip().lower()
    with _lock:
        items = _load()
        existed = key in items
        items[key] = steps.strip()
        _save(items)
    return f"{'Updated' if existed else 'Learned'} routine '{key}'."


def delete(name: str) -> str:
    key = name.strip().lower()
    with _lock:
        items = _load()
        if key not in items:
            return f"No routine called '{key}'."
        del items[key]
        _save(items)
    return f"Deleted routine '{key}'."


def all_text() -> str:
    items = _load()
    if not items:
        return "(none yet)"
    return "\n".join(f"- \"{k}\": {v}" for k, v in items.items())
