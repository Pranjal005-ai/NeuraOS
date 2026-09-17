"""
=========================================================
core/speech.py

Text to speech for Ved.

Author: Pranjal

Run from the PROJECT ROOT:
    python3 -m core.speech            # list voices + demo
    python3 -m core.speech "Namaste"  # say something

WHY THREE BACKENDS
------------------
macOS  -> the `say` command. Ships with Lekha (Hindi),
          Rishi (Indian English) and others. Best quality
          available with zero installation, and it speaks
          Devanagari properly. Mac dev only.

Piper  -> small neural TTS, runs offline on a Pi 5. This
          is the deployment target. Needs voice models
          downloaded per language.

pyttsx3-> fallback. Cross-platform, but on Linux it wraps
          espeak, which sounds robotic and mangles
          Devanagari. Use only if nothing else works.

VOICE PER LANGUAGE
------------------
Hinglish deliberately uses an INDIAN ENGLISH voice, not a
Hindi one. "Aapka naam kya hai" is written in Roman
script, so a Hindi voice would try to read it as English
letters. Rishi reads Roman text with Indian phonetics,
which is exactly what Hinglish needs.
=========================================================
"""

import os
import platform
import shutil
import subprocess
import threading


####################################################
# Voice preferences per language
####################################################

# macOS `say` voice names. Availability varies by system
# -- run `say -v ?` in a terminal to see what you have.
# Missing voices fall back to the system default.
MACOS_VOICES = {
    "English": ["Daniel", "Samantha", "Alex"],
    "Hinglish": ["Rishi", "Veena", "Daniel"],
    "Hindi": ["Lekha", "Rishi"],
    "Marathi": ["Ananya", "Lekha"],
    "Gujarati": ["Lekha"],
    "Rajasthani": ["Lekha"],
}

# Piper model files, relative to PIPER_VOICE_DIR.
PIPER_VOICES = {
    "English": "en_US-lessac-medium.onnx",
    "Hinglish": "en_US-lessac-medium.onnx",
    "Hindi": "hi_IN-pratham-medium.onnx",
}

PIPER_VOICE_DIR = os.path.expanduser("~/piper_voices")

DEFAULT_RATE = 175


####################################################
# Backend detection
####################################################

def _macos_say_available():

    return (
        platform.system() == "Darwin"
        and shutil.which("say") is not None
    )


def _piper_available():

    return shutil.which("piper") is not None


def _pyttsx3_available():

    try:
        import pyttsx3  # noqa: F401
        return True
    except Exception:
        return False


####################################################
# macOS
####################################################

class MacSayBackend:

    name = "macos-say"

    def __init__(self):

        self.available_voices = self._list_voices()

    ##################################################

    @staticmethod
    def _list_voices():

        try:
            output = subprocess.run(
                ["say", "-v", "?"],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout

        except Exception:
            return {}

        voices = {}

        for line in output.splitlines():

            parts = line.split()

            if len(parts) < 2:
                continue

            # Format: "Lekha    hi_IN   # comment"
            name = parts[0]
            locale = parts[1]

            voices[name] = locale

        return voices

    ##################################################

    def voice_for(self, language):

        for candidate in MACOS_VOICES.get(language, []):
            if candidate in self.available_voices:
                return candidate

        return None

    ##################################################

    def speak(self, text, language="English", rate=DEFAULT_RATE):

        command = ["say", "-r", str(rate)]

        voice = self.voice_for(language)

        if voice:
            command += ["-v", voice]

        command.append(text)

        try:
            subprocess.run(command, timeout=30)
            return True

        except Exception as exc:
            print(f"[TTS] say failed: {exc}")
            return False


####################################################
# Piper -- the Pi deployment path
####################################################

class PiperBackend:

    name = "piper"

    def __init__(self, voice_dir=PIPER_VOICE_DIR):

        self.voice_dir = voice_dir

    ##################################################

    def voice_for(self, language):

        model = PIPER_VOICES.get(language)

        if model is None:
            model = PIPER_VOICES.get("English")

        path = os.path.join(self.voice_dir, model)

        return path if os.path.exists(path) else None

    ##################################################

    def speak(self, text, language="English", rate=DEFAULT_RATE):

        model = self.voice_for(language)

        if model is None:
            print(
                f"[TTS] No Piper voice for {language} in "
                f"{self.voice_dir}"
            )
            return False

        try:
            # piper writes raw audio; aplay plays it.
            piper = subprocess.Popen(
                [
                    "piper",
                    "--model", model,
                    "--output-raw"
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )

            player = subprocess.Popen(
                [
                    "aplay",
                    "-r", "22050",
                    "-f", "S16_LE",
                    "-t", "raw",
                    "-"
                ],
                stdin=piper.stdout,
                stderr=subprocess.DEVNULL
            )

            piper.stdin.write(text.encode("utf-8"))
            piper.stdin.close()

            player.wait(timeout=30)

            return True

        except Exception as exc:
            print(f"[TTS] Piper failed: {exc}")
            return False


####################################################
# pyttsx3 fallback
####################################################

class Pyttsx3Backend:

    name = "pyttsx3"

    def __init__(self):

        import pyttsx3

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", DEFAULT_RATE)

    ##################################################

    def speak(self, text, language="English", rate=DEFAULT_RATE):

        try:
            self.engine.setProperty("rate", rate)
            self.engine.say(text)
            self.engine.runAndWait()
            return True

        except Exception as exc:
            print(f"[TTS] pyttsx3 failed: {exc}")
            return False


####################################################
# Speaker
####################################################

class Speaker:

    def __init__(self, backend=None):

        self.backend = backend or self._pick_backend()

        # One utterance at a time. Two overlapping voices
        # is the fastest way to make a robot sound broken.
        self._lock = threading.Lock()

        print(f"[TTS] Backend: {self.backend.name}")

    ##################################################

    @staticmethod
    def _pick_backend():

        if _macos_say_available():
            return MacSayBackend()

        if _piper_available():
            return PiperBackend()

        if _pyttsx3_available():
            return Pyttsx3Backend()

        return None

    ##################################################

    def speak(self, text, language="English", rate=DEFAULT_RATE):

        if not text:
            return False

        if self.backend is None:
            print(f"[VED] {text}")
            return False

        with self._lock:
            return self.backend.speak(text, language, rate)

    ##################################################

    def speak_async(self, text, language="English"):
        """
        Speak without blocking the caller.

        Useful in the vision loop -- a two-second greeting
        should not stall face detection for two seconds.
        """

        thread = threading.Thread(
            target=self.speak,
            args=(text, language),
            daemon=True
        )

        thread.start()

        return thread

    ##################################################

    def voices_for(self, language):
        """Which voice would be used for this language."""

        if hasattr(self.backend, "voice_for"):
            return self.backend.voice_for(language)

        return None


####################################################
# Lazy singleton
#
# interfaces.py looks for core.speech.speak -- this
# module is found automatically, no wiring needed.
####################################################

_speaker = None


def get_speaker():

    global _speaker

    if _speaker is None:
        _speaker = Speaker()

    return _speaker


def speak(text, language="English"):
    """
    Main entry point. Blocks until finished.
    """

    return get_speaker().speak(text, language)


def speak_async(text, language="English"):

    return get_speaker().speak_async(text, language)


####################################################

if __name__ == "__main__":

    import sys

    speaker = get_speaker()

    if speaker.backend is None:
        print("No TTS backend available.")
        sys.exit(1)

    ################################################
    # Say something specific
    ################################################

    if len(sys.argv) > 2:
        speaker.speak(sys.argv[2], sys.argv[1])
        sys.exit(0)

    if len(sys.argv) > 1:
        speaker.speak(sys.argv[1])
        sys.exit(0)

    ################################################
    # Show what's available, then demo
    ################################################

    if isinstance(speaker.backend, MacSayBackend):

        found = speaker.backend.available_voices

        print(f"\n{len(found)} system voices found.\n")

        print("Indian-language voices on this machine:")

        for name, locale in sorted(found.items()):
            if any(
                locale.startswith(code)
                for code in ("hi", "mr", "gu", "ta", "te", "bn", "en_IN")
            ):
                print(f"  {name:<12} {locale}")

    print("\nVoice chosen per language:")

    for language in ["English", "Hinglish", "Hindi", "Marathi"]:
        print(f"  {language:<12} -> {speaker.voices_for(language)}")

    ################################################
    # Demo -- the actual greeting lines
    ################################################

    from vision.greetings import phrase

    print("\nSpeaking...\n")

    for language in ["English", "Hinglish", "Hindi"]:

        line = phrase("greet_first", language, name="Pranjal")

        print(f"  [{language}] {line}")

        speaker.speak(line, language)