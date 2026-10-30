"""Speaking and listening."""

import queue
import re
import threading

from . import personas
from .config import WAKE_WORDS


class Speaker:
    """Speaks text out loud on one background thread (the speech engine isn't thread-safe)."""

    def __init__(self):
        self._q = queue.Queue()
        self._done = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        import pyttsx3

        engine = pyttsx3.init()
        voices = engine.getProperty("voices") or []
        while True:
            text = self._q.get()
            self._apply_persona(engine, voices)
            engine.say(text)
            engine.runAndWait()
            if self._q.empty():
                self._done.set()

    @staticmethod
    def _apply_persona(engine, voices):
        v = personas.PERSONAS[personas.current()]["voice"]
        engine.setProperty("rate", v["rate"])
        for wanted in v["prefer"]:  # pick the first installed voice whose name matches
            for voice in voices:
                if wanted in f"{voice.name} {getattr(voice, 'gender', '')}".lower():
                    engine.setProperty("voice", voice.id)
                    return

    def say(self, text: str, wait: bool = False):
        text = re.sub(r"[*#`_>|]", "", text)  # don't read markdown symbols aloud
        self._done.clear()
        self._q.put(text)
        if wait:
            self._done.wait()


class Listener:
    """Turns microphone speech into text (uses Google's free speech recognition, needs internet)."""

    def __init__(self):
        import speech_recognition as sr

        self.sr = sr
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.mic = sr.Microphone()
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen(self, timeout=None, phrase_limit=15) -> str:
        with self.mic as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except self.sr.WaitTimeoutError:
                return ""
        try:
            return self.recognizer.recognize_google(audio)
        except (self.sr.UnknownValueError, self.sr.RequestError):
            return ""


def split_wake_word(heard: str):
    """Check if `heard` starts with a wake word.

    Returns (mode, rest_of_sentence), where mode is "jarvis"/"ultron" if the user called
    that name (None for "Hey DB"). Returns None if the user wasn't talking to DB.
    """
    low = heard.lower().strip()
    for mode in personas.PERSONAS:
        for w in (f"hey {mode}", f"ok {mode}", f"okay {mode}", mode):
            if low.startswith(w):
                return mode, heard.strip()[len(w):].strip(" ,.!?")
    for w in WAKE_WORDS:
        if low.startswith(w):
            return None, heard.strip()[len(w):].strip(" ,.!?")
    return None
