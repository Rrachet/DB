"""Speaking and listening."""

import queue
import re
import threading

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
        engine.setProperty("rate", 185)
        while True:
            text = self._q.get()
            engine.say(text)
            engine.runAndWait()
            if self._q.empty():
                self._done.set()

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
    """If `heard` starts with a wake word, return the rest of the sentence ('' if none). Else None."""
    low = heard.lower().strip()
    for w in WAKE_WORDS:
        if low.startswith(w):
            return heard[len(w):].strip(" ,.")
    return None
