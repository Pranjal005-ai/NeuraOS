"""
=========================================================
face_engine.py

Face detection + recognition via InsightFace.

Author: Pranjal

WHAT CHANGED
------------
1. BEST-OF-TEMPLATES matching. Each person now holds
   several templates; the score is the highest match
   across them, not a single averaged vector. Enroll in
   daylight AND in a dim room and both work.
2. LOW-LIGHT ENHANCEMENT. Dark frames get CLAHE + gamma
   before detection. This does not create information
   that was never captured, but it does recover faces
   the detector would otherwise miss in an underexposed
   frame.
3. Lazy singleton, CPU context, largest-face selection,
   box-returning recognition (as before).
=========================================================
"""

import numpy as np

from vision.config import (
    FACE_MODEL,
    FACE_CTX_ID,
    FACE_DET_SIZE,
    FACE_RECOGNISE_THRESHOLD,
    LOW_LIGHT_AUTO,
    LOW_LIGHT_BRIGHTNESS,
)

from vision.face_database import load_faces, normalise


class FaceEngine:

    def __init__(self):

        from insightface.app import FaceAnalysis

        print(f"[FACE] Loading InsightFace '{FACE_MODEL}'...")

        self.app = FaceAnalysis(name=FACE_MODEL)

        self.app.prepare(
            ctx_id=FACE_CTX_ID,
            det_size=FACE_DET_SIZE
        )

        self.known_faces = load_faces()

        total = sum(len(t) for t in self.known_faces.values())

        print(
            f"[FACE] Ready. {len(self.known_faces)} person(s), "
            f"{total} template(s)."
        )

    ####################################################

    def reload_database(self):

        self.known_faces = load_faces()

        return len(self.known_faces)

    ####################################################

    @staticmethod
    def _box_of(face):

        x1, y1, x2, y2 = map(int, face.bbox)

        return (x1, y1, x2, y2)

    ####################################################

    @staticmethod
    def _area(face):

        x1, y1, x2, y2 = face.bbox

        return max(0, x2 - x1) * max(0, y2 - y1)

    ####################################################

    @staticmethod
    def _prepare(frame):
        """
        Enhance the frame if it is too dark to detect in.

        Deliberately conservative: a well-lit frame is
        passed through untouched, because enhancing an
        already-good frame only adds noise.
        """

        if not LOW_LIGHT_AUTO or frame is None:
            return frame

        from vision.camera import frame_brightness, enhance_low_light

        if frame_brightness(frame) >= LOW_LIGHT_BRIGHTNESS:
            return frame

        return enhance_low_light(frame)

    ####################################################

    def detect_faces(self, frame, enhance=True):
        """
        All faces in the frame, largest first.
        """

        if frame is None:
            return []

        if enhance:
            frame = self._prepare(frame)

        faces = self.app.get(frame)

        return sorted(faces, key=self._area, reverse=True)

    ####################################################

    def get_face(self, frame):
        """The largest (closest) face, or None."""

        faces = self.detect_faces(frame)

        return faces[0] if faces else None

    ####################################################

    def register(self, frame):
        """Embedding for the closest face, or None."""

        face = self.get_face(frame)

        if face is None:
            return None

        return normalise(face.embedding)

    ####################################################

    def match(self, embedding):
        """
        Compare one embedding against every template.

        Returns (name, score).

        The score is the BEST match across that person's
        templates. Using the mean would drag a good
        daylight match down because the dim-room template
        happened to disagree -- which is exactly the
        behaviour we are trying to remove.
        """

        if not self.known_faces:
            return "Unknown", 0.0

        query = normalise(embedding)

        best_name = "Unknown"
        best_score = -1.0

        for name, templates in self.known_faces.items():

            # templates is (N, D), query is (D,)
            scores = templates @ query

            score = float(scores.max())

            if score > best_score:
                best_score = score
                best_name = name

        if best_score < FACE_RECOGNISE_THRESHOLD:
            return "Unknown", best_score

        return best_name, best_score

    ####################################################

    def recognize(self, frame):
        """
        Identify the closest face.

        Always a 3-tuple (name, score, box); box is None
        when no face was found.
        """

        face = self.get_face(frame)

        if face is None:
            return "Unknown", 0.0, None

        name, score = self.match(face.embedding)

        return name, score, self._box_of(face)

    ####################################################

    def recognize_all(self, frame):
        """
        Every face in the frame, largest first.

        Returns [{"name", "score", "box"}].
        """

        results = []

        for face in self.detect_faces(frame):

            name, score = self.match(face.embedding)

            results.append(
                {
                    "name": name,
                    "score": round(score, 3),
                    "box": self._box_of(face),
                }
            )

        return results

    ####################################################

    def score_against(self, frame, name):
        """
        Diagnostic: how well does this frame match one
        specific person? Useful for tuning thresholds --
        stand in your dim room and watch the number.
        """

        templates = self.known_faces.get(name)

        if templates is None:
            return None

        face = self.get_face(frame)

        if face is None:
            return None

        scores = templates @ normalise(face.embedding)

        return {
            "best": float(scores.max()),
            "worst": float(scores.min()),
            "mean": float(scores.mean()),
            "templates": int(len(templates)),
        }


####################################################
# Lazy singleton
####################################################

_engine = None


def get_engine():

    global _engine

    if _engine is None:
        _engine = FaceEngine()

    return _engine


def recognize(frame):

    return get_engine().recognize(frame)


def recognize_all(frame):

    return get_engine().recognize_all(frame)


def register(frame):

    return get_engine().register(frame)


def reload_database():

    return get_engine().reload_database()