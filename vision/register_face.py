"""
=========================================================
register_face.py

Enrolls a person into Ved's face database.

Run from the PROJECT ROOT:
    python3 -m vision.register_face

Author: Pranjal

WHAT CHANGED
------------
Enrollment now ADDS a template set rather than replacing
everything. Enroll once in daylight, once in your dim
room, once with glasses on -- each session adds coverage
and Ved matches against the best of them.

The script measures frame brightness and labels the
session automatically ("daylight" / "indoor" / "dim"), so
`python3 -m vision.face_database` shows you which
conditions a person is actually covered for.
=========================================================
"""

import time

import cv2

from vision.camera import (
    get_camera,
    release_camera,
    frame_brightness,
)
from vision.config import (
    ENROLL_SAMPLES,
    ENROLL_MIN_INTERVAL,
    LOW_LIGHT_BRIGHTNESS,
    LOW_LIGHT_FPS,
)
from vision.augment import augmented_templates
from vision.face_database import (
    add_templates,
    average_embeddings,
    normalise,
    list_faces,
    face_info,
)
from vision.face_engine import get_engine


MIN_FACE_WIDTH = 90


def condition_label(brightness):

    if brightness >= 120:
        return "bright"

    if brightness >= 70:
        return "indoor"

    if brightness >= 35:
        return "dim"

    return "dark"


def capture_sample(engine, frame):
    """
    Returns (embedding, message).
    """

    faces = engine.detect_faces(frame)

    if not faces:
        return None, "No face detected"

    if len(faces) > 1:
        return None, "More than one face -- only you in frame"

    face = faces[0]

    x1, _, x2, _ = map(int, face.bbox)

    if (x2 - x1) < MIN_FACE_WIDTH:
        return None, "Too far -- move closer"

    return normalise(face.embedding), "Captured"


def main():

    print("=" * 52)
    print("VED  --  FACE ENROLLMENT")
    print("=" * 52)

    known = list_faces()

    if known:
        print("Already enrolled:")

        for person in known:
            info = face_info(person) or {}
            conditions = {
                s.get("condition")
                for s in info.get("sessions", [])
            }
            print(
                f"  {person:<16} "
                f"{info.get('templates', '?')} templates  "
                f"{', '.join(sorted(c for c in conditions if c))}"
            )

    name = input("\nEnter person's name: ").strip()

    if not name:
        print("Name cannot be empty.")
        return

    if name in known:
        print(
            f"\n'{name}' is already enrolled. This session "
            "will ADD to their coverage, not replace it."
        )

    engine = get_engine()

    cam = get_camera()

    if cam.wait_for_frame() is None:
        print("No frames from camera.")
        return

    ################################################
    # Assess the light
    ################################################

    time.sleep(0.5)

    brightness = frame_brightness(cam.get_frame())

    label = condition_label(brightness)

    print(f"\nScene brightness: {brightness:.0f}/255  ({label})")

    if brightness < LOW_LIGHT_BRIGHTNESS:

        print("Dark scene -- enabling low-light mode.")

        cam.set_low_light(True, fps=LOW_LIGHT_FPS)

        time.sleep(1.5)

        brightness = frame_brightness(cam.get_frame())
        label = condition_label(brightness)

        print(f"After adjustment: {brightness:.0f}/255  ({label})")

    print()
    print(f"Capturing {ENROLL_SAMPLES} samples [{label}].")
    print("Turn your head slowly between captures --")
    print("varied angles matter more than perfect ones.")
    print()
    print("  SPACE = capture     ESC = cancel")
    print()

    embeddings = []
    captured_frames = []
    last_capture = 0.0
    status = "Ready"

    try:
        while len(embeddings) < ENROLL_SAMPLES:

            frame = cam.get_frame()

            if frame is None:
                continue

            preview = frame.copy()

            for face in engine.detect_faces(preview):
                x1, y1, x2, y2 = map(int, face.bbox)
                cv2.rectangle(
                    preview, (x1, y1), (x2, y2), (0, 255, 0), 2
                )

            cv2.putText(
                preview,
                f"{len(embeddings)}/{ENROLL_SAMPLES}  "
                f"[{label}]  {status}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2
            )

            cv2.imshow("Ved -- Register Face", preview)

            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                print("\nCancelled.")
                return

            if key != 32:
                continue

            if time.time() - last_capture < ENROLL_MIN_INTERVAL:
                continue

            embedding, status = capture_sample(engine, frame)

            if embedding is None:
                print(f"  skipped: {status}")
                continue

            embeddings.append(embedding)
            captured_frames.append(frame.copy())
            last_capture = time.time()

            print(f"  sample {len(embeddings)}/{ENROLL_SAMPLES}")

    finally:
        cv2.destroyAllWindows()
        release_camera()

    if not embeddings:
        print("Nothing captured.")
        return

    ################################################
    # Save
    #
    # Registration happens ONCE, so we manufacture the
    # lighting variation the person will never come back
    # to provide: darkened, brightened, warmed, noisier
    # versions of these same frames, each embedded as its
    # own template.
    ################################################

    print("\nBuilding templates from captured frames...")

    engine = get_engine()

    templates = augmented_templates(
        engine,
        captured_frames,
        base_label=label
    )

    if not templates:
        # Augmentation failed entirely -- fall back to
        # the plain averaged embedding so the session is
        # not wasted.
        add_templates(
            name,
            average_embeddings(embeddings),
            condition=label
        )

        total = 1
        print("  (augmentation failed, stored plain template)")

    else:
        for condition, embedding in templates:
            total = add_templates(
                name, embedding, condition=condition
            )
            print(f"  + {condition}")

    engine.reload_database()

    print()
    print("=" * 52)
    print(f"Enrolled '{name}' from {len(embeddings)} samples")
    print(f"-> {len(templates) or 1} templates covering")
    print(f"   several lighting conditions.")
    print(f"'{name}' now has {total} template(s) total.")
    print("=" * 52)
    print()
    print("No need to re-register in other lighting --")
    print("Ved will also learn new conditions on its own")
    print("whenever it recognises someone confidently.")


if __name__ == "__main__":
    main()