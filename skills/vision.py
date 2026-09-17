"""
=========================================================
vision.py

Vision Skill

Author: NeuraOS

CHANGED
-------
Was opening its own cv2.VideoCapture(0) instead of going
through vision/camera.py. Two problems with that:

1. Doesn't work on the Pi at all -- the CSI camera goes
   through the Picamera2 backend, not cv2.VideoCapture.
2. Even on the Mac, a second capture handle on the same
   device fights the shared background capture thread.

get_frame() is the same wrapper every other vision module
now uses, and it works on both backends transparently.
=========================================================
"""

from vision.camera import get_frame
from vision.object_detector import (
    detect_objects,
    describe_detections
)


def see():

    frame = get_frame()

    if frame is None:
        return "I cannot see anything right now."

    detections = detect_objects(frame)

    return describe_detections(detections)