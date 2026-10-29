"""Settings for DB. Change them with environment variables."""

import os
from pathlib import Path

# Where DB keeps its memory and reminders (C:\Users\<you>\.db_assistant).
DATA_DIR = Path(os.environ.get("DB_DATA_DIR", Path.home() / ".db_assistant"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = DATA_DIR / "memory.json"
REMINDERS_FILE = DATA_DIR / "reminders.json"

# Claude settings (only used when ANTHROPIC_API_KEY is your AI key).
MODEL = os.environ.get("DB_MODEL", "claude-opus-5-5")
# low = faster and cheaper, high = more careful.
EFFORT = os.environ.get("DB_EFFORT", "medium")

# Set DB_AUTO_APPROVE=1 to let DB run commands without asking you first.
AUTO_APPROVE = os.environ.get("DB_AUTO_APPROVE", "0") == "1"

# Words the speech recognizer may hear when you say "Hey DB".
WAKE_WORDS = ["hey db", "hey d b", "hey dee bee", "hey deebee", "hey tb", "hi db", "okay db", "ok db"]

# Start a fresh conversation after this many messages (memories are kept).
MAX_HISTORY_MESSAGES = 80
