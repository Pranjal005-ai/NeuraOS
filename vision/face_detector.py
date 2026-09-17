"""
=========================================================
face_detector.py

Cheap "is there a face at all?" check using Haar cascade.

Author: Pranjal

WHAT THIS IS FOR
----------------
This is NOT the recognition path -- face_engine does
that. Haar runs in ~3ms where InsightFace takes ~80ms on
a Pi 5, so this is the gate: run it every frame, and only
wake the expensive model when a face actually appears.

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. detect(frame) takes the frame as an ARGUMENT instead
   of calling get_frame() itself. When each module grabs
   its own frame, face detection, QR and OCR all end up
   working on different moments in time.
2. Lazy singleton; the cascade is no longer built at
   import.
=========================================================
"""

import cv2


class FaceDetector:

    def __init__(self):

        path = (
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        self.detector = cv2.CascadeClassifier(path)

        if self.detector.empty():
            raise RuntimeError(
                f"Could not load Haar cascade: {path}"
            )

    ##################################################

    def detect(self, frame, min_size=(80, 80)):
        """
        Returns a list of (x, y, w, h), largest first.
        """

        if frame is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Evens out backlit faces, which is the usual
        # failure case in a hotel lobby or ward corridor.
        gray = cv2.equalizeHist(gray)

        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=min_size
        )

        faces = list(faces)

        faces.sort(key=lambda f: f[2] * f[3], reverse=True)

        return faces

    ##################################################

    def has_face(self, frame):

        return len(self.detect(frame)) > 0

    ##################################################

    def draw(self, frame, faces):

        for (x, y, w, h) in faces:

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 255),
                2
            )

        return frame


####################################################
# Lazy singleton
####################################################

_detector = None


def get_detector():

    global _detector

    if _detector is None:
        _detector = FaceDetector()

    return _detector


def detect_faces(frame, min_size=(80, 80)):

    return get_detector().detect(frame, min_size)


def has_face(frame):

    return get_detector().has_face(frame)


def draw_faces(frame, faces):

    return get_detector().draw(frame, faces)