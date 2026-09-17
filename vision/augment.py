"""
=========================================================
augment.py

Synthesises lighting variation from enrollment frames.

Author: Pranjal

WHY THIS EXISTS
---------------
Registration happens ONCE. A hotel guest gives you thirty
seconds at check-in under lobby lighting, and you will
never get them back to re-enroll at dusk. But the face
they present at 9pm in a dim corridor produces a
noticeably different embedding.

So instead of asking the person for more sessions, we
manufacture the sessions from the frames we already have:
darken them, brighten them, flatten the contrast, add
sensor noise. Each variant becomes its own template.

WHAT THIS CAN AND CANNOT DO
---------------------------
CAN: cover the range between "well lit" and "dim but
visible". Gamma and contrast changes are a decent
approximation of real exposure differences.

CANNOT: invent detail that was never captured. A synthetic
"dark" version of a bright photo is not the same as a real
dark photo -- real darkness brings sensor noise, motion
blur from longer exposure, and lost shadow detail that no
transform reproduces faithfully.

So this narrows the gap. It does not close it. If a face
is genuinely invisible to the sensor, this changes
nothing -- that remains an IR problem.
=========================================================
"""

import cv2
import numpy as np


####################################################
# Primitives
####################################################

_GAMMA_CACHE = {}


def _gamma_table(gamma):

    key = round(gamma, 3)

    if key not in _GAMMA_CACHE:

        inv = 1.0 / max(0.01, key)

        _GAMMA_CACHE[key] = np.array(
            [((i / 255.0) ** inv) * 255 for i in range(256)]
        ).astype(np.uint8)

    return _GAMMA_CACHE[key]


def adjust_gamma(image, gamma):
    """
    gamma < 1 darkens, gamma > 1 brightens.

    Gamma rather than a flat brightness offset because
    real exposure changes are multiplicative -- shadows
    lose far more than highlights.
    """

    return cv2.LUT(image, _gamma_table(gamma))


def adjust_contrast(image, factor):
    """
    factor < 1 flattens. Dim scenes lose contrast as
    well as brightness; this is the second half of that.
    """

    return cv2.convertScaleAbs(image, alpha=factor, beta=0)


def add_sensor_noise(image, sigma=6.0):
    """
    Gaussian noise, approximating high-ISO grain.

    A camera pushed to high gain in a dark room produces
    visible speckle, and the detector does respond to it.
    Training a template on clean-but-dark frames alone
    misses that.
    """

    noise = np.random.normal(0, sigma, image.shape)

    return np.clip(
        image.astype(np.float32) + noise, 0, 255
    ).astype(np.uint8)


def soften(image, ksize=3):
    """
    Slight blur, standing in for the softness of a
    longer exposure or a slightly missed focus.
    """

    return cv2.GaussianBlur(image, (ksize, ksize), 0)


def warm_shift(image, amount=12):
    """
    Push toward tungsten. Indian interiors are full of
    warm bulbs; daylight enrollment does not cover them.
    """

    out = image.astype(np.int16)

    out[:, :, 0] -= amount      # less blue
    out[:, :, 2] += amount      # more red

    return np.clip(out, 0, 255).astype(np.uint8)


def cool_shift(image, amount=12):
    """Push toward fluorescent / daylight LED."""

    out = image.astype(np.int16)

    out[:, :, 0] += amount
    out[:, :, 2] -= amount

    return np.clip(out, 0, 255).astype(np.uint8)


####################################################
# Variant sets
####################################################

def lighting_variants(image):
    """
    A spread of plausible lighting conditions.

    Returns [(label, image)]. Labels are stored as the
    template's condition so you can see the coverage in
    face_database.

    IMPORTANT: the variant set depends on how bright the
    SOURCE is. Darkening an already-dark frame produces a
    near-black image whose embedding is noise -- and
    storing that as a template actively makes recognition
    worse. So a dim enrollment gets brightening variants
    instead, and a very dark one gets almost nothing.
    """

    if image is None:
        return []

    from vision.camera import frame_brightness

    brightness = frame_brightness(image)

    ################################################
    # Too dark to augment usefully
    ################################################

    if brightness < 45:
        # Nothing to work with. Lifting it adds noise,
        # darkening it destroys what little is there.
        return []

    ################################################
    # Dim source -- only brighten
    ################################################

    if brightness < 80:
        return [
            ("indoor", adjust_gamma(image, 1.35)),
            ("bright", adjust_gamma(image, 1.7)),
            ("warm", warm_shift(image)),
        ]

    ################################################
    # Well-lit source -- the full spread
    ################################################

    return [
        ("dim", add_sensor_noise(adjust_gamma(image, 0.55), 5.0)),
        ("dark", add_sensor_noise(
            adjust_contrast(adjust_gamma(image, 0.35), 0.85), 8.0
        )),
        ("bright", adjust_gamma(image, 1.45)),
        ("warm", warm_shift(adjust_gamma(image, 0.8))),
        ("soft", soften(adjust_gamma(image, 0.7))),
    ]


def variants_for(image, include=None):
    """
    Pick a subset by label.
    """

    all_variants = lighting_variants(image)

    if include is None:
        return all_variants

    wanted = set(include)

    return [v for v in all_variants if v[0] in wanted]


####################################################
# Building templates
####################################################

def augmented_templates(engine, frames, base_label="enrolled"):
    """
    Turn enrollment frames into a labelled template set.

    engine: a FaceEngine
    frames: the raw BGR frames captured during enrollment

    Returns [(condition_label, embedding)].

    One template per condition, averaged across all the
    frames for that condition -- averaging WITHIN a
    condition removes noise, which is exactly what we
    want, while keeping conditions separate.
    """

    from vision.face_database import normalise

    if not frames:
        return []

    buckets = {base_label: []}

    for frame in frames:

        # The unmodified frame.
        embedding = _embed(engine, frame)

        if embedding is not None:
            buckets[base_label].append(embedding)

        # Synthetic conditions.
        for label, variant in lighting_variants(frame):

            embedding = _embed(engine, variant)

            if embedding is None:
                continue

            buckets.setdefault(label, []).append(embedding)

    templates = []

    for label, embeddings in buckets.items():

        if not embeddings:
            continue

        stacked = normalise(np.stack(embeddings))

        templates.append((label, normalise(stacked.mean(axis=0))))

    return templates


def _embed(engine, image):
    """
    Largest face in the image, as a normalised embedding.

    Returns None if the augmentation destroyed the face --
    which does happen at the aggressive end, and is
    exactly why we check rather than assume.
    """

    from vision.face_database import normalise

    faces = engine.detect_faces(image, enhance=False)

    if not faces:
        return None

    return normalise(faces[0].embedding)


####################################################

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 -m vision.augment <image.jpg>")
        sys.exit(1)

    image = cv2.imread(sys.argv[1])

    if image is None:
        print("Could not read image.")
        sys.exit(1)

    from vision.camera import frame_brightness

    print(f"Original brightness: {frame_brightness(image):.0f}")

    for label, variant in lighting_variants(image):

        out = f"augment_{label}.jpg"

        cv2.imwrite(out, variant)

        print(
            f"  {label:<8} brightness "
            f"{frame_brightness(variant):>5.0f}  -> {out}"
        )