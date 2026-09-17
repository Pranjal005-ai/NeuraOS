"""
=========================================================
person_follow.py

Follows the person currently locked via
target_tracker.set_target(), confirming identity with
face recognition.

Run from the PROJECT ROOT:
    python3 -m vision.person_follow

Author: Pranjal

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. SAFETY: the whole loop is wrapped in try/finally so
   the motors ALWAYS stop -- on exception, on ESC, on
   Ctrl+C. Previously a crash mid-forward() left the
   gear motors driving with nothing left running to
   stop them.
2. Imports find_target (which exists) instead of the
   old broken name, and takes the bounding box from it.
3. Uses the shared camera wrapper -- works on the Pi's
   CSI camera, and does not fight other vision modules
   for frames.
4. Recognition runs on a budget, not every frame. On a
   Pi 5 InsightFace takes ~80ms; calling it every frame
   caps the control loop at ~12Hz and makes steering
   sluggish. Between recognitions we coast on the last
   known box.
5. Wrapped in a function instead of running at import.

STILL TO DO ON REAL HARDWARE
----------------------------
Add a timeout in the ESP32 firmware: if no motor command
arrives for ~500ms, stop. Software watchdogs cannot
protect you from a USB cable falling out.
=========================================================
"""

import time

import cv2

from vision.camera import get_camera, release_camera
from vision.config import FOLLOW_WATCHDOG_SECONDS
from vision.face_lock import find_target
from vision.follow_logic import follow_person, describe
from vision.target_tracker import has_target, get_target

from motion.motor_controller import (
    forward,
    backward,
    left,
    right,
    stop,
)


# How often to re-run face recognition (seconds).
RECOGNITION_INTERVAL = 0.20

# Give up on a target this long after last seeing them.
TARGET_LOST_AFTER = 1.0


COMMANDS = {
    "MOVE_FORWARD": forward,
    "FOLLOW": forward,
    "MOVE_BACKWARD": backward,
    "TURN_LEFT": left,
    "TURN_LEFT_FAST": left,
    "TURN_RIGHT": right,
    "TURN_RIGHT_FAST": right,
    "STOP": stop,
}


def draw_guides(frame, width, height):

    cv2.line(
        frame, (width // 2, 0), (width // 2, height), (255, 0, 0), 1
    )

    for fraction in (0.40, 0.60):
        x = int(width * fraction)
        cv2.line(frame, (x, 0), (x, height), (0, 255, 255), 1)


def run(show_preview=True):

    cam = get_camera()

    if cam.wait_for_frame() is None:
        print("No frames from camera.")
        return

    print("=" * 52)
    print("VED PERSON FOLLOWING")
    print("Press ESC to quit")
    print("=" * 52)

    last_command = None
    last_recognition = 0.0
    last_seen = 0.0

    box = None
    score = 0.0

    try:
        while True:

            frame = cam.get_frame()

            if frame is None:
                continue

            height, width = frame.shape[:2]

            if show_preview:
                draw_guides(frame, width, height)

            ############################################
            # No target locked
            ############################################

            if not has_target():

                if last_command != "STOP":
                    stop()
                    last_command = "STOP"

                if show_preview:
                    cv2.putText(
                        frame, "No target set", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 0, 255), 2
                    )
                    cv2.imshow("Ved Person Following", frame)

                    if cv2.waitKey(1) & 0xFF == 27:
                        break

                continue

            ############################################
            # Recognition, on a budget
            ############################################

            now = time.time()

            if now - last_recognition >= RECOGNITION_INTERVAL:

                found, new_box, new_score = find_target(frame)

                last_recognition = now

                if found:
                    box = new_box
                    score = new_score
                    last_seen = now
                elif now - last_seen > TARGET_LOST_AFTER:
                    box = None
                    score = 0.0

            ############################################
            # Drive
            ############################################

            if box is not None:

                command = follow_person(box, width)

                COMMANDS.get(command, stop)()

                if command != last_command:
                    print(f"-> {describe(command, box, width)}")
                    last_command = command

                if show_preview:

                    x1, y1, x2, y2 = box

                    cv2.rectangle(
                        frame, (x1, y1), (x2, y2), (0, 255, 0), 2
                    )

                    cv2.putText(
                        frame,
                        f"Following {get_target()} ({score:.2f})",
                        (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 255), 2
                    )

                    cv2.putText(
                        frame, command, (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 2
                    )

            else:

                if last_command != "STOP":
                    stop()
                    last_command = "STOP"
                    print("-> STOP (target lost)")

                if show_preview:
                    cv2.putText(
                        frame,
                        f"Searching for {get_target()}...",
                        (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 0, 255), 2
                    )

            ############################################
            # Watchdog
            #
            # If a frame takes longer than this, we have
            # been driving blind. Stop and reassess.
            ############################################

            if time.time() - now > FOLLOW_WATCHDOG_SECONDS:
                stop()
                last_command = "STOP"
                print("-> STOP (loop stalled)")

            if show_preview:

                cv2.imshow("Ved Person Following", frame)

                if cv2.waitKey(1) & 0xFF == 27:
                    break

    except KeyboardInterrupt:
        print("\nInterrupted.")

    finally:
        # This block is the whole safety story.
        stop()
        cv2.destroyAllWindows()
        release_camera()
        print("Motors stopped, camera released.")


if __name__ == "__main__":
    run()