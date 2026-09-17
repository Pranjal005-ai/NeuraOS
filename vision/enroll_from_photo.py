"""
=========================================================
enroll_from_photo.py

Enrolls people into Ved's face database from image files
instead of the live camera.

Author: Pranjal

USAGE
-----
One person, explicit files:

    python3 -m vision.enroll_from_photo \
        --name pranjal photos/a.jpg photos/b.jpg

One person, a whole folder:

    python3 -m vision.enroll_from_photo \
        --name pranjal --folder photos/pranjal

Many people at once -- one subfolder per person:

    vision/enroll_photos/
        pranjal/     img1.jpg  img2.jpg  img3.jpg
        rahul/       photo.png
        priya/       a.jpg  b.jpg

    python3 -m vision.enroll_from_photo --batch

WHY MULTIPLE PHOTOS STILL MATTER
--------------------------------
The averaging is the same as live enrollment: several
angles beat one perfect shot. Three photos from a phone
gallery usually outperform one studio headshot.
=========================================================
"""

import argparse
import sys
from pathlib import Path

import cv2

from vision.config import VISION_DIR
from vision.face_database import (
    average_embeddings,
    normalise,
    save_face,
    list_faces,
)
from vision.face_engine import get_engine


PHOTO_DIR = VISION_DIR / "enroll_photos"

VALID_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
}

# Photos are usually higher resolution than a webcam
# frame, so we can demand a bigger face than the live
# path does. A tiny face in a group shot makes a poor
# embedding.
MIN_FACE_WIDTH = 60


####################################################
# Single image
####################################################

def embedding_from_image(engine, path):
    """
    Returns (embedding, message). embedding is None if
    the photo is unusable.
    """

    image = cv2.imread(str(path))

    if image is None:
        return None, "could not read file"

    faces = engine.detect_faces(image)

    if not faces:
        return None, "no face found"

    # detect_faces returns largest first. In a group
    # photo the largest face is usually the subject --
    # but warn, because "usually" is not "always".
    face = faces[0]

    x1, y1, x2, y2 = map(int, face.bbox)

    width = x2 - x1

    if width < MIN_FACE_WIDTH:
        return None, f"face too small ({width}px)"

    note = "ok"

    if len(faces) > 1:
        note = f"ok (WARNING: {len(faces)} faces, used largest)"

    return normalise(face.embedding), note


####################################################
# One person
####################################################

def enroll_person(name, paths, engine=None, quiet=False):
    """
    Returns the number of photos successfully used.
    """

    engine = engine or get_engine()

    embeddings = []

    for path in paths:

        embedding, note = embedding_from_image(engine, path)

        if embedding is None:
            if not quiet:
                print(f"    SKIP  {path.name}: {note}")
            continue

        embeddings.append(embedding)

        if not quiet:
            print(f"    USE   {path.name}: {note}")

    if not embeddings:
        print(f"  No usable photos for '{name}'.")
        return 0

    averaged = average_embeddings(embeddings)

    save_face(name, averaged, samples=len(embeddings))

    print(
        f"  Enrolled '{name}' from "
        f"{len(embeddings)}/{len(paths)} photo(s)."
    )

    return len(embeddings)


####################################################
# Helpers
####################################################

def images_in(folder):

    folder = Path(folder)

    if not folder.is_dir():
        return []

    return sorted(
        p for p in folder.iterdir()
        if p.suffix.lower() in VALID_SUFFIXES
    )


def confirm_overwrite(name):

    if name not in list_faces():
        return True

    answer = input(
        f"  '{name}' already enrolled. Overwrite? [y/N]: "
    ).strip().lower()

    return answer == "y"


####################################################
# Batch
####################################################

def run_batch(engine):

    if not PHOTO_DIR.exists():

        PHOTO_DIR.mkdir(parents=True, exist_ok=True)

        print(f"Created {PHOTO_DIR}")
        print("Add one subfolder per person, then re-run.")
        return

    people = [p for p in sorted(PHOTO_DIR.iterdir()) if p.is_dir()]

    if not people:
        print(f"No person folders inside {PHOTO_DIR}")
        return

    print(f"Found {len(people)} person folder(s).\n")

    total = 0

    for folder in people:

        name = folder.name

        photos = images_in(folder)

        print(f"{name}  ({len(photos)} photo(s))")

        if not photos:
            print("    no images, skipping")
            continue

        if not confirm_overwrite(name):
            print("    skipped")
            continue

        if enroll_person(name, photos, engine):
            total += 1

        print()

    print(f"Done. {total} person(s) enrolled.")


####################################################
# Main
####################################################

def main():

    parser = argparse.ArgumentParser(
        description="Enroll faces from photo files."
    )

    parser.add_argument("images", nargs="*", type=Path)
    parser.add_argument("--name", help="person's name")
    parser.add_argument("--folder", help="folder of photos")
    parser.add_argument(
        "--batch",
        action="store_true",
        help=f"enroll every subfolder of {PHOTO_DIR}"
    )

    args = parser.parse_args()

    engine = get_engine()

    ################################################
    # Batch mode
    ################################################

    if args.batch:
        run_batch(engine)
        return

    ################################################
    # Single person
    ################################################

    if not args.name:
        parser.error("--name is required (or use --batch)")

    paths = list(args.images)

    if args.folder:
        paths.extend(images_in(args.folder))

    paths = [p for p in paths if p.exists()]

    if not paths:
        parser.error("no readable image files given")

    print(f"\n{args.name}  ({len(paths)} photo(s))")

    if not confirm_overwrite(args.name):
        print("Cancelled.")
        return

    count = enroll_person(args.name, paths, engine)

    if count:
        engine.reload_database()


if __name__ == "__main__":

    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)