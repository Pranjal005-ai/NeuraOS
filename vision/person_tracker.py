"""
person_tracker.py

Tracks a person using YOLO detections.

Future:
- DeepSORT
- ByteTrack
- StrongSORT
"""

from core.state import (
    state_manager,
    RobotState
)

from motion.motor_controller import (
    forward,
    left,
    right,
    stop
)

FRAME_CENTER_X = 320

CENTER_MARGIN = 50

MIN_BOX_WIDTH = 180


class PersonTracker:

    def __init__(self):

        self.following = False

    # --------------------------------------------------

    def start(self):

        self.following = True

        state_manager.set(
            RobotState.FOLLOWING
        )

        print("[FOLLOW] Started")

    # --------------------------------------------------

    def stopFollowing(self):

        self.following = False

        stop()

        state_manager.set(
            RobotState.IDLE
        )

        print("[FOLLOW] Stopped")

    # --------------------------------------------------

    def update(self, detections):

        if not self.following:
            return

        person = None

        for obj in detections:

            if obj["label"] == "person":

                person = obj

                break

        if person is None:

            stop()

            return

        x1, y1, x2, y2 = person["box"]

        center_x = (x1 + x2) // 2

        width = x2 - x1

        # -----------------------
        # Turn Left
        # -----------------------

        if center_x < FRAME_CENTER_X - CENTER_MARGIN:

            left()

            return

        # -----------------------
        # Turn Right
        # -----------------------

        if center_x > FRAME_CENTER_X + CENTER_MARGIN:

            right()

            return

        # -----------------------
        # Too Far
        # -----------------------

        if width < MIN_BOX_WIDTH:

            forward()

            return

        stop()


tracker = PersonTracker()