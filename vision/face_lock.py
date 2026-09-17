"""
=========================================================
face_lock.py

Decides whether the person Ved is following is visible
in the current frame.

Author: Pranjal

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. Renamed get_target() -> find_target(). The old name
   collided with target_tracker.get_target(), which
   means something completely different ("who are we
   following" vs "who is in this frame"). person_follow
   imports both, so the collision was a real bug waiting
   to happen.
2. Returns (found, box, score) -- the contract
   person_follow.py already expected. The old version
   returned a name string, so the import was broken
   anyway.
3. Confirms the face matches the LOCKED target, rather
   than reporting whoever happens to be closest.
4. No module-level engine construction.
=========================================================
"""

from vision.config import FACE_LOCK_THRESHOLD
from vision.face_engine import get_engine
from vision.target_tracker import get_target, has_target


def find_target(frame):
    """
    Look for the currently locked target.

    Returns (found, box, score):
        found -> bool
        box   -> (x1, y1, x2, y2) or None
        score -> cosine similarity, 0.0 if absent
    """

    if frame is None or not has_target():
        return False, None, 0.0

    wanted = get_target()

    engine = get_engine()

    best_box = None
    best_score = 0.0

    # Check every face, not just the closest -- the
    # person being followed may not be the nearest one.
    for result in engine.recognize_all(frame):

        if result["name"] != wanted:
            continue

        if result["score"] > best_score:
            best_score = result["score"]
            best_box = result["box"]

    found = (
        best_box is not None
        and best_score >= FACE_LOCK_THRESHOLD
    )

    return found, best_box, best_score


def identify(frame):
    """
    Who is in front of Ved right now, regardless of
    whether a target is locked.

    Returns (name, score, box).
    """

    return get_engine().recognize(frame)