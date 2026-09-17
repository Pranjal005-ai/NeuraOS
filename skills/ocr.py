"""
=========================================================
ocr.py

Skill:
Read text from the camera.

Author: NeuraOS

CHANGED
-------
vision/ocr.py no longer exposes a module-level `ocr`
object -- it's now a lazy singleton (get_ocr()), because
the old `ocr = OCR()` at module scope downloaded ~500MB
of EasyOCR models on first import, blocking on the
network any time this file was reached in an import
chain. read() also now takes a frame argument instead of
grabbing its own.

Imported as `vision_read_text` to avoid shadowing this
file's own read_text(), which is the name assistant.py
imports.
=========================================================
"""

from vision.ocr import read_text as vision_read_text
from vision.camera import get_frame


def read_text():

    frame = get_frame()

    if frame is None:
        return "I can't see anything right now."

    text = vision_read_text(frame)

    if text is None:
        return "I couldn't read any text."

    print("OCR Result")
    print(text)

    return f"I read: {text}"