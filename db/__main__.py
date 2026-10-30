"""Start DB.

    python -m db            type to DB
    python -m db --speak    type to DB, DB answers out loud
    python -m db --voice    say "Hey Jarvis ..." / "Hey Ultron ..." and talk hands-free
"""

import argparse
import os
import sys

from . import llm, personas, reminders
from .brain import Brain


def main():
    parser = argparse.ArgumentParser(prog="db", description="DB, your personal assistant")
    parser.add_argument("--voice", action="store_true", help="hands-free: wake word + speech")
    parser.add_argument("--speak", action="store_true", help="read replies out loud")
    args = parser.parse_args()

    if not llm.available():
        print("DB needs an AI key. The easiest free one is Google Gemini:")
        print("  1. Get a key at https://aistudio.google.com/apikey")
        print('  2. In PowerShell run:  setx GEMINI_API_KEY "your-key"   then open a new window.')
        print("Groq (GROQ_API_KEY), OpenRouter (OPENROUTER_API_KEY) and Claude (ANTHROPIC_API_KEY) also work.")
        sys.exit(1)

    speaker = None
    listener = None
    if args.voice or args.speak:
        from .voice import Speaker

        speaker = Speaker()
    if args.voice:
        from .voice import Listener

        print("Setting up the microphone...")
        listener = Listener()

    def out(text):
        print(f"\nDB: {text}\n")
        if speaker:
            speaker.say(text)

    def confirm(question: str) -> bool:
        print(f"\nDB wants to: {question}")
        if listener:
            speaker.say("I need your OK. Should I go ahead? Say yes or no.", wait=True)
            answer = listener.listen(timeout=8, phrase_limit=4).lower()
            print(f"(you said: {answer or 'nothing'})")
            return any(w in answer for w in ("yes", "yeah", "sure", "go ahead", "ok", "do it", "haan"))
        return input("Allow? [y/N] ").strip().lower() in ("y", "yes")

    def on_status(status):
        print(f"  {status}", flush=True)

    brain = Brain(confirm)
    print(f"Using: {brain.provider_names}")
    reminders.start_watcher(lambda msg: out(f"Reminder: {msg}"))

    def handle(text):
        if text.strip().lower().lstrip("/") in personas.PERSONAS and text.strip().startswith("/"):
            mode = text.strip().lower().lstrip("/")
            personas.set_current(mode)
            brain.reset()
            out(f"{personas.PERSONAS[mode]['title']} online.")
            return
        if text.strip().lower() in ("/new", "new chat"):
            brain.reset()
            out("Starting fresh. I still remember what you told me to remember.")
            return
        try:
            out(brain.ask(text, on_status))
        except llm.LLMError as e:
            print(f"  (details: {e})")
            if "connection failed" in str(e):
                out("I can't reach the internet right now.")
            elif "HTTP 429" in str(e):
                out("I've hit my free limit for now. Try again in a minute, or add another free key.")
            elif "HTTP 401" in str(e) or "HTTP 403" in str(e) or "API key not valid" in str(e):
                out("My API key isn't working. Check the key you set.")
            else:
                out("Something went wrong getting an answer. Try again.")

    if listener:
        title = personas.PERSONAS[personas.current()]["title"]
        out(f"{title} online. Say 'Hey Jarvis' or 'Hey Ultron' followed by what you need.")
        from .voice import split_wake_word

        while True:
            heard = listener.listen()
            if not heard:
                continue
            woke = split_wake_word(heard)
            if woke is None:
                continue  # not talking to DB
            mode, command = woke
            if mode and mode != personas.current():
                personas.set_current(mode)
                brain.reset()
                out(f"{personas.PERSONAS[mode]['title']} online.")
            print(f"You: {heard}")
            if not command:
                speaker.say("Yes?", wait=True)
                command = listener.listen(timeout=6)
                if not command:
                    continue
                print(f"You: {command}")
            if command.lower() in ("goodbye", "shut down", "exit", "stop listening"):
                out("Goodbye.")
                speaker.say("", wait=True)
                break
            handle(command)
    else:
        title = personas.PERSONAS[personas.current()]["title"]
        out(f"{title} online. Type what you need. '/jarvis' or '/ultron' switches mode, '/new' starts fresh, 'exit' quits.")
        while True:
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in ("exit", "quit", "bye"):
                out("Goodbye.")
                break
            handle(text)


if __name__ == "__main__":
    main()
