"""Start DB.

    python -m db            type to DB
    python -m db --speak    type to DB, DB answers out loud
    python -m db --voice    say "Hey DB ..." and talk hands-free
"""

import argparse
import os
import sys

import anthropic

from . import reminders
from .brain import Brain


def main():
    parser = argparse.ArgumentParser(prog="db", description="DB, your personal assistant")
    parser.add_argument("--voice", action="store_true", help="hands-free: wake word + speech")
    parser.add_argument("--speak", action="store_true", help="read replies out loud")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("DB needs an Anthropic API key. Run this once in PowerShell, then open a new window:")
        print('  setx ANTHROPIC_API_KEY "sk-ant-..."')
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
    reminders.start_watcher(lambda msg: out(f"Reminder: {msg}"))

    def handle(text):
        if text.strip().lower() in ("/new", "new chat"):
            brain.reset()
            out("Starting fresh. I still remember what you told me to remember.")
            return
        try:
            out(brain.ask(text, on_status))
        except anthropic.AuthenticationError:
            out("My API key isn't working. Check ANTHROPIC_API_KEY.")
        except anthropic.RateLimitError:
            out("I'm being rate limited. Try again in a minute.")
        except anthropic.APIConnectionError:
            out("I can't reach the internet right now.")
        except anthropic.APIError as e:
            out(f"Something went wrong talking to Claude: {e}")

    if listener:
        out("DB is online. Say 'Hey DB' followed by what you need.")
        from .voice import split_wake_word

        while True:
            heard = listener.listen()
            if not heard:
                continue
            command = split_wake_word(heard)
            if command is None:
                continue  # not talking to DB
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
        out("DB is online. Type what you need. '/new' starts a fresh chat, 'exit' quits.")
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
