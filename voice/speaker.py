import pyttsx3
import threading


class Speaker:
    def __init__(self):
        self._lock = threading.Lock()
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 175)
        voices = self.engine.getProperty("voices")
        for v in voices:
            if "turkish" in v.name.lower() or "tr" in v.id.lower():
                self.engine.setProperty("voice", v.id)
                break

    def say(self, text: str):
        def _speak():
            with self._lock:
                self.engine.say(text)
                self.engine.runAndWait()
        threading.Thread(target=_speak, daemon=True).start()
