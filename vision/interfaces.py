"""
=========================================================
interfaces.py

Thin adapters between the vision stack and the rest of
NeuraOS (speech, TTS, the animated face).

Author: Pranjal

WHY ADAPTERS
------------
The greeter needs to speak, listen and change Ved's
expression. Those live in other packages whose exact
function names may differ from what this file guesses.

Rather than hard-import and crash, each adapter tries a
few likely names and falls back to the terminal. That
means greeter.py RUNS TODAY on your Mac with typed input,
and starts talking the moment the real modules line up.

If your function names differ, fix them HERE -- one file,
not scattered through the greeter.
=========================================================
"""


####################################################
# Text to speech
####################################################

def _load_speaker():

    # Try the likely homes for a speak() function.
    for module_name, attr in [
        ("core.speech", "speak"),
        ("speech.tts", "speak"),
        ("core.tts", "speak"),
        ("assistant", "speak"),
    ]:
        try:
            module = __import__(module_name, fromlist=[attr])
            return getattr(module, attr)
        except Exception:
            continue

    return None


_speak_fn = None
_speak_loaded = False


def speak(text):
    """
    Say something. Falls back to printing.
    """

    global _speak_fn, _speak_loaded

    if not _speak_loaded:
        _speak_fn = _load_speaker()
        _speak_loaded = True

        if _speak_fn is None:
            print("[VOICE] No TTS module found -- printing instead.")

    print(f"[VED] {text}")

    if _speak_fn is not None:
        try:
            _speak_fn(text)
        except Exception as exc:
            print(f"[VOICE] TTS failed: {exc}")


####################################################
# Speech to text
####################################################

def _load_listener():

    for module_name, attr in [
        ("core.speech_listener", "listen"),
        ("speech.speech_listener", "listen"),
        ("core.speech", "listen"),
        ("speech_listener", "listen"),
    ]:
        try:
            module = __import__(module_name, fromlist=[attr])
            return getattr(module, attr)
        except Exception:
            continue

    return None


_listen_fn = None
_listen_loaded = False


def listen(prompt="", timeout=6.0):
    """
    Capture a spoken reply. Falls back to typed input, so
    the whole flow is testable without a microphone.

    Returns the text, or None.
    """

    global _listen_fn, _listen_loaded

    if not _listen_loaded:
        _listen_fn = _load_listener()
        _listen_loaded = True

        if _listen_fn is None:
            print("[VOICE] No STT module found -- using keyboard.")

    if _listen_fn is not None:

        try:
            result = _listen_fn()

            if result:
                print(f"[HEARD] {result}")
                return str(result).strip()

            return None

        except Exception as exc:
            print(f"[VOICE] STT failed: {exc}")

    # Keyboard fallback.
    try:
        return input(f"{prompt} > ").strip() or None
    except (EOFError, KeyboardInterrupt):
        return None


####################################################
# Face expression
####################################################

def _load_face():

    for module_name in [
        "face.face_controller",
        "face.face",
        "core.face_controller",
    ]:
        try:
            return __import__(module_name, fromlist=["*"])
        except Exception:
            continue

    return None


_face_module = None
_face_loaded = False

VALID_EXPRESSIONS = {
    "idle", "happy", "listening", "thinking",
    "speaking", "surprised", "sad", "sleeping", "wink",
}


def set_expression(name):
    """
    Drive Ved's animated face.

    Tries face_controller.set_expression("happy"), then a
    bare happy() method, then gives up quietly. The
    greeter should never crash because the display isn't
    running.
    """

    global _face_module, _face_loaded

    if name not in VALID_EXPRESSIONS:
        return

    if not _face_loaded:
        _face_module = _load_face()
        _face_loaded = True

        if _face_module is None:
            print("[FACE] No face controller found -- skipping.")

    if _face_module is None:
        return

    try:
        if hasattr(_face_module, "set_expression"):
            _face_module.set_expression(name)
            return

        for holder in ("face", "controller", "face_controller"):

            obj = getattr(_face_module, holder, None)

            if obj is None:
                continue

            if hasattr(obj, name):
                getattr(obj, name)()
                return

            if hasattr(obj, "set_expression"):
                obj.set_expression(name)
                return

    except Exception as exc:
        print(f"[FACE] Could not set expression: {exc}")