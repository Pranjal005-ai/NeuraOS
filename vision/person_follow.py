"""
person_follow.py

Follows the specific person currently set as the target
(via target_tracker.set_target), using face recognition
to confirm identity every frame.
"""

import cv2

from vision.face_lock import find_target
from vision.follow_logic import follow_person
from vision.target_tracker import has_target, get_target

from motion.motor_controller import (
    forward,
    backward,
    left,
    right,
    stop
)

# -----------------------------
# Open Camera
# -----------------------------
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera not found")
    exit()

print("=" * 50)
print("VED PERSON FOLLOWING STARTED")
print("Press ESC to quit")
print("=" * 50)

last_command = ""

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    frame_width = frame.shape[1]
    frame_height = frame.shape[0]

    # -----------------------------
    # Draw Center Line
    # -----------------------------
    cv2.line(
        frame,
        (frame_width // 2, 0),
        (frame_width // 2, frame_height),
        (255, 0, 0),
        2
    )

    # -----------------------------
    # Draw Dead Zone
    # -----------------------------
    left_zone = int(frame_width * 0.45)
    right_zone = int(frame_width * 0.55)

    cv2.line(
        frame,
        (left_zone, 0),
        (left_zone, frame_height),
        (0, 255, 255),
        2
    )

    cv2.line(
        frame,
        (right_zone, 0),
        (right_zone, frame_height),
        (0, 255, 255),
        2
    )

    # -----------------------------
    # No target selected
    # -----------------------------
    if not has_target():

        if last_command != "STOP":

            stop()
            last_command = "STOP"

        cv2.putText(
            frame,
            "No target set",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        cv2.imshow("Ved Person Following", frame)

        if cv2.waitKey(1) == 27:
            break

        continue

    # -----------------------------
    # Find Target
    # -----------------------------
    found, box, score = find_target(frame)

    if found:

        x1, y1, x2, y2 = box

        # NOTE:
        # follow_logic() currently uses face size instead of body size.
        # You will tune its thresholds after testing on the real robot.

        movement = follow_person(
            box,
            frame_width
        )

        # -----------------------------
        # Motor Commands
        # -----------------------------

        if movement in ("MOVE_FORWARD", "FOLLOW"):

            forward()

        elif movement == "MOVE_BACKWARD":

            backward()

        elif movement in ("TURN_LEFT", "TURN_LEFT_FAST"):

            left()

        elif movement in ("TURN_RIGHT", "TURN_RIGHT_FAST"):

            right()

        elif movement == "STOP":

            stop()

        # -----------------------------
        # Console Logging
        # -----------------------------

        if movement != last_command:

            print(
                "➡",
                movement,
                f"(score={score:.2f})"
            )

            last_command = movement

        # -----------------------------
        # Draw Face
        # -----------------------------

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"Following: {get_target()} ({score:.2f})",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            movement,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    else:

        # -----------------------------
        # Target Lost
        # -----------------------------

        if last_command != "STOP":

            stop()

            last_command = "STOP"

            print("➡ STOP (Target Lost)")

        cv2.putText(
            frame,
            f"Searching for {get_target()}...",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

    # -----------------------------
    # Display
    # -----------------------------

    cv2.imshow(
        "Ved Person Following",
        frame
    )

    if cv2.waitKey(1) == 27:
        break

# -----------------------------
# Cleanup
# -----------------------------

stop()

cap.release()

cv2.destroyAllWindows()