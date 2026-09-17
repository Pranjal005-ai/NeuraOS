"""
=========================================================
face_recognition.py

Live face recognition preview.

Run from the PROJECT ROOT:
    python3 -m vision.face_recognition

Author: Pranjal

BUGS FIXED FROM THE PREVIOUS VERSION
------------------------------------
1. `name` was used before assignment -- the lock block
   sat ABOVE `name, score = result`.
2. Imported lock_target from target_tracker, which only
   defines set_target. ImportError on line 2, so the file
   never ran at all.
3. `if result is None` never fired, because recognize()
   returned a tuple even with no face. "Unknown" was
   getting locked as a follow target.
4. cv2.VideoCapture(0) bypassed the camera wrapper and
   cannot see the Pi's CSI camera.
=========================================================
"""

import cv2

from vision.camera import get_camera, release_camera
from vision.config import FACE_LOCK_THRESHOLD
from vision.face_engine import get_engine
from vision.target_tracker import set_target, get_target


def colour_for(name):

    return (0, 255, 0) if name != "Unknown" else (0, 0, 255)


def main():

    engine = get_engine()

    cam = get_camera()

    if cam.wait_for_frame() is None:
        print("No frames from camera.")
        return

    print("=" * 52)
    print("VED FACE RECOGNITION")
    print("  L   = lock the closest known face as target")
    print("  ESC = quit")
    print("=" * 52)

    last_seen = None

    try:
        while True:

            frame = cam.get_frame()

            if frame is None:
                continue

            results = engine.recognize_all(frame)

            for person in results:

                name = person["name"]
                score = person["score"]
                x1, y1, x2, y2 = person["box"]

                colour = colour_for(name)

                cv2.rectangle(
                    frame, (x1, y1), (x2, y2), colour, 2
                )

                cv2.putText(
                    frame,
                    f"{name} ({score:.2f})",
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    colour,
                    2
                )

            # Closest recognised person, if any.
            closest = results[0] if results else None

            if closest and closest["name"] != last_seen:
                last_seen = closest["name"]
                print(
                    f"[SEE] {closest['name']} "
                    f"({closest['score']:.2f})"
                )

            target = get_target()

            cv2.putText(
                frame,
                f"Target: {target or 'none'}   FPS {cam.fps()}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )

            cv2.imshow("Ved Face Recognition", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                break

            if key in (ord("l"), ord("L")):

                if (
                    closest
                    and closest["name"] != "Unknown"
                    and closest["score"] >= FACE_LOCK_THRESHOLD
                ):
                    set_target(closest["name"])
                    print(f"[LOCK] Target set to {closest['name']}")
                else:
                    print("[LOCK] No confident known face to lock")

    finally:
        cv2.destroyAllWindows()
        release_camera()


if __name__ == "__main__":
    main()