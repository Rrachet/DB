"""Long-term memory: facts about you that DB keeps between sessions."""

import json
import threading
import time

from .config import MEMORY_FILE

_lock = threading.Lock()


def _load():
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(items):
    MEMORY_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def remember(fact: str) -> str:
    with _lock:
        items = _load()
        new_id = max((m["id"] for m in items), default=0) + 1
        items.append({"id": new_id, "fact": fact.strip(), "saved": time.strftime("%Y-%m-%d %H:%M")})
        _save(items)
    return f"Saved memory #{new_id}."


def forget(memory_id: int) -> str:
    with _lock:
        items = _load()
        kept = [m for m in items if m["id"] != memory_id]
        if len(kept) == len(items):
            return f"No memory #{memory_id}."
        _save(kept)
    return f"Forgot memory #{memory_id}."


def all_memories_text() -> str:
    items = _load()
    if not items:
        return "(nothing saved yet)"
    return "\n".join(f"#{m['id']}: {m['fact']}" for m in items)
