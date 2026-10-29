"""The things DB can do on your computer."""

import base64
import io
import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

from . import llm, memory, reminders
from .config import AUTO_APPROVE

MAX_OUTPUT = 10_000


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


TOOLS = [
    {
        "name": "run_powershell",
        "description": (
            "Run a PowerShell command on the user's Windows PC and get its output. Use it for system info, "
            "managing files and folders, settings, installing with winget, and any task without a dedicated tool. "
            "The user is asked to approve every command before it runs."
        ),
        "input_schema": _obj(
            {
                "command": {"type": "string", "description": "The PowerShell command to run."},
                "reason": {"type": "string", "description": "One short sentence telling the user why."},
            },
            ["command", "reason"],
        ),
    },
    {
        "name": "open_app",
        "description": "Open an app, file or folder by name or path, e.g. 'notepad', 'calc', 'spotify', 'C:\\Users\\me\\Documents'.",
        "input_schema": _obj({"target": {"type": "string"}}, ["target"]),
    },
    {
        "name": "open_url",
        "description": "Open a web page in the user's default browser.",
        "input_schema": _obj({"url": {"type": "string"}}, ["url"]),
    },
    {
        "name": "list_files",
        "description": "List the files and folders inside a folder.",
        "input_schema": _obj({"path": {"type": "string"}}, ["path"]),
    },
    {
        "name": "read_file",
        "description": "Read a text file.",
        "input_schema": _obj({"path": {"type": "string"}}, ["path"]),
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a text file. The user approves overwriting an existing file.",
        "input_schema": _obj({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    },
    {
        "name": "take_screenshot",
        "description": "Look at the user's screen right now. Use it when the user asks about what is on screen.",
        "input_schema": _obj({}, []),
    },
    {
        "name": "get_datetime",
        "description": "Get the current local date and time.",
        "input_schema": _obj({}, []),
    },
    {
        "name": "remember",
        "description": "Save a lasting fact about the user (preferences, people, routines) so you know it in future sessions.",
        "input_schema": _obj({"fact": {"type": "string"}}, ["fact"]),
    },
    {
        "name": "forget",
        "description": "Delete a saved memory by its number.",
        "input_schema": _obj({"memory_id": {"type": "integer"}}, ["memory_id"]),
    },
    {
        "name": "set_reminder",
        "description": (
            "Remind the user of something later. Give 'in_minutes' for relative times, or 'when' as a local "
            "ISO date-time like 2026-10-29T18:30 (call get_datetime first if you need today's date)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "when": {"type": "string"},
                "in_minutes": {"type": "number"},
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_reminders",
        "description": "List upcoming reminders.",
        "input_schema": _obj({}, []),
    },
    {
        "name": "cancel_reminder",
        "description": "Cancel a reminder by its number.",
        "input_schema": _obj({"reminder_id": {"type": "integer"}}, ["reminder_id"]),
    },
    {
        "name": "search_web",
        "description": "Search the web for current information (news, prices, facts, how-tos).",
        "input_schema": _obj({"query": {"type": "string"}}, ["query"]),
    },
]

# Claude has its own built-in web search, so it gets that instead of search_web.
CLAUDE_TOOLS = [t for t in TOOLS if t["name"] != "search_web"] + [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
]


def _plain_schema(schema):
    s = {k: v for k, v in schema.items() if k != "additionalProperties"}
    if not s.get("properties"):
        s.pop("required", None)
    return s


# Same tools in the format Gemini, Groq and OpenRouter use.
OPENAI_TOOLS = [
    {"type": "function", "function": {"name": t["name"], "description": t["description"],
                                      "parameters": _plain_schema(t["input_schema"])}}
    for t in TOOLS
]


def _trim(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT else text[:MAX_OUTPUT] + "\n...(output cut off)"


def _screenshot():
    import mss
    from PIL import Image

    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])  # all screens together
        img = Image.frombytes("RGB", shot.size, shot.rgb)
    img.thumbnail((1568, 1568))  # big enough to read, small enough to send quickly
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}]


def run(name: str, args: dict, confirm) -> str | list:
    """Run one tool. `confirm(question) -> bool` asks the user. Returns text or content blocks."""
    if name == "run_powershell":
        command = args["command"]
        if not AUTO_APPROVE and not confirm(f"{args.get('reason', '')}\n  > {command}\nRun this command?"):
            return "The user declined to run this command."
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            return "Error: the command took longer than 2 minutes and was stopped."
        out = (proc.stdout or "") + (("\nERRORS:\n" + proc.stderr) if proc.stderr else "")
        return _trim(out.strip() or f"(no output, exit code {proc.returncode})")

    if name == "open_app":
        subprocess.Popen(["cmd", "/c", "start", "", args["target"]], shell=False)
        return f"Opened {args['target']}."

    if name == "open_url":
        webbrowser.open(args["url"])
        return f"Opened {args['url']}."

    if name == "list_files":
        p = Path(os.path.expandvars(os.path.expanduser(args["path"])))
        entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        return _trim("\n".join(("[folder] " if e.is_dir() else "") + e.name for e in entries) or "(empty)")

    if name == "read_file":
        p = Path(os.path.expandvars(os.path.expanduser(args["path"])))
        return _trim(p.read_text(encoding="utf-8", errors="replace"))

    if name == "write_file":
        p = Path(os.path.expandvars(os.path.expanduser(args["path"])))
        if p.exists() and not AUTO_APPROVE and not confirm(f"Overwrite {p}?"):
            return "The user declined to overwrite the file."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"], encoding="utf-8")
        return f"Wrote {p}."

    if name == "take_screenshot":
        return _screenshot()

    if name == "search_web":
        return _trim(llm.google_search(args["query"]))

    if name == "get_datetime":
        return datetime.now().strftime("%A %d %B %Y, %H:%M")

    if name == "remember":
        return memory.remember(args["fact"])
    if name == "forget":
        return memory.forget(int(args["memory_id"]))

    if name == "set_reminder":
        return reminders.add(args["message"], args.get("when"), args.get("in_minutes"))
    if name == "list_reminders":
        return reminders.list_all()
    if name == "cancel_reminder":
        return reminders.cancel(int(args["reminder_id"]))

    return f"Error: unknown tool {name}."
