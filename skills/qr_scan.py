"""
=========================================================
qr_scan.py

Skill:
Scan a QR code and return its contents.

Author: NeuraOS

CHANGED
-------
qr_scanner.py no longer exposes a module-level `scanner`
object, and scan() now takes a frame instead of pulling
one from the camera itself (so the scanner can be fed
frames from the shared capture thread, same reasoning as
camera.py's single-reader design). This file was still on
the old interface, which is what ImportError'd.
=========================================================
"""

from vision.qr_scanner import get_scanner
from vision.camera import get_frame


def scan_qr():

    frame = get_frame()

    if frame is None:
        return "I can't see anything right now."

    result = get_scanner().scan(frame)

    if result is None:
        return "I couldn't find any QR code."

    print("QR Found")
    print(result["text"])

    return f"I scanned: {result['text']}"