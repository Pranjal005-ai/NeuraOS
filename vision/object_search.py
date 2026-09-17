"""
object_search.py

Searches for a requested object using
YOLO object detection.
"""

import time

from core.state import (
    state_manager,
    RobotState
)

from motion.motor_controller import (
    left,
    stop,
)

from vision.object_detector import (
    detect_objects,
)

from vision.camera import get_frame


class ObjectSearcher:

    def __init__(self):

        self.searching = False

    # -------------------------------------------------

    def find(self, target):

        print(f"[SEARCH] Looking for {target}")

        state_manager.set(
            RobotState.SEARCHING
        )

        self.searching = True

        while self.searching:

            frame = get_frame()

            detections = detect_objects(frame)

            for obj in detections:

                if obj["label"] == target:

                    stop()

                    self.searching = False

                    state_manager.set(
                        RobotState.IDLE
                    )

                    return True

            # Rotate slowly while searching

            left()

            time.sleep(0.3)

        return False


searcher = ObjectSearcher()