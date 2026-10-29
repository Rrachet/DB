"""Reminders that pop up as Windows notifications (and are spoken in voice mode)."""

import json
import threading
import time
from datetime import datetime, timedelta

from .config import REMINDERS_FILE

_lock = threading.Lock()


def _load():
    try:
        return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(items):
    REMINDERS_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def add(message: str, when: str | None = None, in_minutes: float | None = None) -> str:
    if in_minutes is not None:
        due = datetime.now() + timedelta(minutes=float(in_minutes))
    elif when:
        try:
            due = datetime.fromisoformat(when)
        except ValueError:
            return "Error: 'when' must look like 2026-10-29T18:30."
    else:
        return "Error: give either 'when' or 'in_minutes'."
    with _lock:
        items = _load()
        new_id = max((r["id"] for r in items), default=0) + 1
        items.append({"id": new_id, "message": message, "due": due.isoformat(timespec="minutes")})
        _save(items)
    return f"Reminder #{new_id} set for {due:%a %d %b %H:%M}."


def list_all() -> str:
    items = _load()
    if not items:
        return "No reminders."
    return "\n".join(f"#{r['id']} at {r['due']}: {r['message']}" for r in items)


def cancel(reminder_id: int) -> str:
    with _lock:
        items = _load()
        kept = [r for r in items if r["id"] != reminder_id]
        if len(kept) == len(items):
            return f"No reminder #{reminder_id}."
        _save(kept)
    return f"Cancelled reminder #{reminder_id}."


def _notify(message: str):
    try:
        from plyer import notification

        notification.notify(title="DB reminder", message=message, app_name="DB", timeout=10)
    except Exception:
        pass  # Notifications are a bonus; the console/voice alert still happens.


def start_watcher(on_due):
    """Check every 20 seconds and call on_due(message) for reminders that are due."""

    def loop():
        while True:
            now = datetime.now()
            with _lock:
                items = _load()
                due = [r for r in items if datetime.fromisoformat(r["due"]) <= now]
                if due:
                    _save([r for r in items if r not in due])
            for r in due:
                _notify(r["message"])
                on_due(r["message"])
            time.sleep(20)

    threading.Thread(target=loop, daemon=True).start()
