"""
=========================================================
follow_logic.py

Turns a face bounding box into a movement command.

Author: Pranjal

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. Thresholds retuned for FACE boxes. The old numbers
   (stop above 380px, forward below 140px) were body-box
   sizes. A face 380px wide means their nose is touching
   the lens, so STOP could never fire and Ved would drive
   into people.
2. Distance is checked before steering, so Ved stops
   rather than continuing to turn into someone standing
   right in front of it.
3. Zones are fractions of frame width, so this still
   works if you change camera resolution.
=========================================================
"""

from vision.config import (
    FOLLOW_FACE_TOO_CLOSE,
    FOLLOW_FACE_TOO_FAR,
    FOLLOW_DEAD_ZONE,
    FOLLOW_FAST_ZONE,
)


def follow_person(box, frame_width):
    """
    box -> (x1, y1, x2, y2) of the target's FACE

    Returns one of:
        STOP, MOVE_FORWARD, MOVE_BACKWARD,
        TURN_LEFT, TURN_LEFT_FAST,
        TURN_RIGHT, TURN_RIGHT_FAST,
        FOLLOW
    """

    if box is None or frame_width <= 0:
        return "STOP"

    x1, _, x2, _ = box

    face_width = x2 - x1
    center_x = (x1 + x2) / 2.0

    # Offset from centre: -0.5 (hard left) .. +0.5 (right)
    offset = (center_x / frame_width) - 0.5

    ####################################################
    # Distance first -- safety before aesthetics
    ####################################################

    if face_width >= FOLLOW_FACE_TOO_CLOSE * 1.35:
        return "MOVE_BACKWARD"

    if face_width >= FOLLOW_FACE_TOO_CLOSE:
        return "STOP"

    ####################################################
    # Steering
    ####################################################

    if abs(offset) > FOLLOW_FAST_ZONE:
        return "TURN_LEFT_FAST" if offset < 0 else "TURN_RIGHT_FAST"

    if abs(offset) > FOLLOW_DEAD_ZONE:
        return "TURN_LEFT" if offset < 0 else "TURN_RIGHT"

    ####################################################
    # Aligned -- close the gap
    ####################################################

    if face_width <= FOLLOW_FACE_TOO_FAR:
        return "MOVE_FORWARD"

    return "FOLLOW"


def describe(command, box, frame_width):
    """Human-readable, for logs and debugging."""

    if box is None:
        return "no target"

    x1, _, x2, _ = box

    return (
        f"{command} "
        f"(face={x2 - x1}px, "
        f"offset={((x1 + x2) / 2.0 / frame_width - 0.5):+.2f})"
    )