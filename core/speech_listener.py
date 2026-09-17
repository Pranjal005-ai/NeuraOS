"""
=========================================================
core/speech_listener.py

Speech to text for Ved, using Whisper.

Author: Pranjal

Run from the PROJECT ROOT:
    python3 -m core.speech_listener

INSTALL
-------
    pip install faster-whisper sounddevice numpy

faster-whisper rather than openai-whisper: same models,
roughly 4x faster on CPU, much lower memory. That
difference decides whether this is usable on a Pi 5.

MODEL SIZE
----------
    tiny   ~ 75MB   fast, weak on Hindi
    base   ~ 145MB  good balance -- the default here
    small  ~ 480MB  noticeably better Hindi, slower
    medium ~ 1.5GB  Mac only, too heavy for a Pi

WHY LANGUAGE AUTO-DETECT MATTERS
--------------------------------
Whisper reports which language it heard. That means Ved
can answer a Hindi speaker in Hindi WITHOUT being told
to -- the language preference becomes an observation
rather than a question. parse_language() only ever
worked because we asked; this makes asking optional.

A CAUTION ON HINGLISH
---------------------
Whisper transcribes code-switched speech inconsistently.
"Mera naam Pranjal hai" may come back as Devanagari, as
Roman, or as a mix, depending on the surrounding words.
Do not rely on the script -- match on content.
=========================================================
"""

import queue
import sys
import threading
import time


MODEL_SIZE = "base"

SAMPLE_RATE = 16000
CHANNELS = 1

# Silence detection. Recording stops after this much
# quiet, which is what makes listening feel responsive
# instead of a fixed five-second block.
SILENCE_THRESHOLD = 0.012
SILENCE_DURATION = 1.0

MAX_RECORD_SECONDS = 12.0
MIN_SPEECH_SECONDS = 0.3

# Whisper hallucinates confident text from pure noise.
# Below this average probability, treat it as nothing.
MIN_CONFIDENCE = -1.0


class SpeechListener:

    def __init__(self, model_size=MODEL_SIZE, device="cpu"):

        self.model_size = model_size
        self.device = device

        self._model = None
        self._lock = threading.Lock()

    ####################################################

    def load(self):
        """
        Load the model. Lazy -- takes several seconds and
        holds real memory, so it should not happen at
        import.
        """

        if self._model is not None:
            return self._model

        from faster_whisper import WhisperModel

        print(f"[STT] Loading Whisper '{self.model_size}'...")

        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type="int8"
        )

        print("[STT] Ready.")

        return self._model

    ####################################################

    def record(
        self,
        max_seconds=MAX_RECORD_SECONDS,
        silence_duration=SILENCE_DURATION
    ):
        """
        Record until the speaker stops, or the cap is hit.

        Returns a float32 numpy array, or None.
        """

        import numpy as np
        import sounddevice as sd

        audio_queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            audio_queue.put(indata.copy())

        chunks = []

        started_speaking = False
        silence_started = None

        start = time.time()

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=int(SAMPLE_RATE * 0.1),
                callback=callback
            ):

                while True:

                    if time.time() - start > max_seconds:
                        break

                    try:
                        chunk = audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    chunks.append(chunk)

                    level = float(np.abs(chunk).mean())

                    if level > SILENCE_THRESHOLD:

                        started_speaking = True
                        silence_started = None

                        continue

                    # Only start counting silence once
                    # they've actually said something --
                    # otherwise we cut off before they
                    # begin.
                    if not started_speaking:
                        continue

                    if silence_started is None:
                        silence_started = time.time()

                    elif time.time() - silence_started > silence_duration:
                        break

        except Exception as exc:
            print(f"[STT] Recording failed: {exc}")
            return None

        if not chunks or not started_speaking:
            return None

        audio = np.concatenate(chunks, axis=0).flatten()

        if len(audio) < SAMPLE_RATE * MIN_SPEECH_SECONDS:
            return None

        return audio

    ####################################################

    def transcribe(self, audio, language=None):
        """
        Returns {"text", "language", "confidence"} or None.

        language=None lets Whisper detect it, which is the
        interesting case. Pass a code ("hi", "en") to
        force it when you already know.
        """

        if audio is None or not len(audio):
            return None

        model = self.load()

        try:
            segments, info = model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False
            )

            segments = list(segments)

        except Exception as exc:
            print(f"[STT] Transcription failed: {exc}")
            return None

        if not segments:
            return None

        text = " ".join(s.text.strip() for s in segments).strip()

        if not text:
            return None

        confidence = sum(
            getattr(s, "avg_logprob", -1.0) for s in segments
        ) / len(segments)

        # Whisper will confidently transcribe silence as
        # "Thank you." or similar. Reject low-confidence
        # output rather than acting on a hallucination.
        if confidence < MIN_CONFIDENCE:
            print(f"[STT] Discarded low-confidence: {text!r}")
            return None

        return {
            "text": text,
            "language": info.language,
            "language_probability": round(
                info.language_probability, 2
            ),
            "confidence": round(confidence, 2),
        }

    ####################################################

    def listen(self, language=None, max_seconds=MAX_RECORD_SECONDS):
        """
        Record, then transcribe. Returns text or None.

        This is the signature interfaces.py expects.
        """

        with self._lock:

            audio = self.record(max_seconds=max_seconds)

            if audio is None:
                return None

            result = self.transcribe(audio, language)

        if result is None:
            return None

        return result["text"]

    ####################################################

    def listen_detailed(self, language=None):
        """
        Same, but returns the language and confidence too.
        """

        with self._lock:

            audio = self.record()

            if audio is None:
                return None

            return self.transcribe(audio, language)


####################################################
# Whisper language codes -> our language names
####################################################

WHISPER_TO_LANGUAGE = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "gu": "Gujarati",
    "ur": "Hindi",        # spoken Urdu ~ spoken Hindi
    "ne": "Hindi",        # Nepali often mis-tags as Hindi
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
}


def language_from_whisper(code, script_is_roman=False):
    """
    Map a Whisper language code to a phrase-bank language.

    If Whisper says Hindi but the text came back in Roman
    script, the speaker was almost certainly using
    Hinglish -- which wants an Indian English voice, not
    a Devanagari one.
    """

    language = WHISPER_TO_LANGUAGE.get(code, "English")

    if language == "Hindi" and script_is_roman:
        return "Hinglish"

    return language


def is_roman_script(text):
    """
    True if the text is mostly Latin characters.
    """

    if not text:
        return True

    letters = [c for c in text if c.isalpha()]

    if not letters:
        return True

    roman = sum(1 for c in letters if ord(c) < 128)

    return roman / len(letters) > 0.6


####################################################
# Lazy singleton
#
# interfaces.py looks for core.speech_listener.listen,
# so this wires up automatically.
####################################################

_listener = None


def get_listener(model_size=MODEL_SIZE):

    global _listener

    if _listener is None:
        _listener = SpeechListener(model_size)

    return _listener


def listen(language=None):

    return get_listener().listen(language)


def listen_detailed(language=None):

    return get_listener().listen_detailed(language)


def detect_language(text, whisper_code):
    """
    Best guess at which phrase-bank language to reply in.
    """

    return language_from_whisper(
        whisper_code,
        is_roman_script(text)
    )


####################################################

if __name__ == "__main__":

    print("=" * 52)
    print("VED SPEECH LISTENER")
    print("=" * 52)

    try:
        import sounddevice  # noqa: F401
    except ImportError:
        print("\nMissing dependency:")
        print("  pip install faster-whisper sounddevice numpy")
        sys.exit(1)

    listener = get_listener()

    listener.load()

    print("\nSpeak after the prompt. Ctrl+C to quit.")
    print("Try English, then Hindi, then Hinglish.\n")

    try:
        while True:

            input("Press ENTER, then speak... ")

            result = listener.listen_detailed()

            if result is None:
                print("  (heard nothing)\n")
                continue

            reply_language = detect_language(
                result["text"],
                result["language"]
            )

            print(f"  Text     : {result['text']}")
            print(
                f"  Language : {result['language']} "
                f"({result['language_probability']}) "
                f"-> reply in {reply_language}"
            )
            print(f"  Confidence: {result['confidence']}\n")

    except KeyboardInterrupt:
        print("\nStopped.")