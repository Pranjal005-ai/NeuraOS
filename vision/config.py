"""
=========================================================
config.py

Shared configuration for Ved's vision stack.

Author: Pranjal

WHY THIS FILE EXISTS
--------------------
Thresholds were previously duplicated: face_engine used
0.45 and face_lock used 0.60. Mismatched thresholds are
how you end up with a person who is good enough to
follow but "Unknown" to greet. One source of truth.

Paths are resolved from this file's location, never from
the current working directory -- otherwise everything
breaks when run from face/, or under systemd at boot.
=========================================================
"""

from pathlib import Path


####################################################
# Paths
####################################################

VISION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VISION_DIR.parent

FACE_DB_DIR = VISION_DIR / "known_faces"
CALIBRATION_FILE = VISION_DIR / "camera.pkl"
YOLO_MODEL_PATH = PROJECT_ROOT / "yolov8n.pt"


####################################################
# Face recognition
####################################################

# InsightFace model pack.
#   buffalo_l  ~ 300MB, best accuracy, heavy on a Pi
#   buffalo_sc ~  16MB, plenty at conversational range
#
# CHANGING THIS INVALIDATES EVERY ENROLLED FACE.
# Embeddings are not portable across models. The database
# now stores which model created them and refuses to load
# mismatches, instead of silently scoring noise.
FACE_MODEL = "buffalo_sc"

# -1 = CPU. Requesting 0 (GPU) on a Pi makes InsightFace
# log a wall of errors before falling back anyway.
FACE_CTX_ID = -1

# 320 is ~4x faster than 640 and still detects faces
# well past 2 metres. Raise if you need long range.
FACE_DET_SIZE = (320, 320)

# Cosine similarity thresholds.
#   RECOGNISE -> "I think I know who this is"
#   LOCK      -> "confident enough to follow them"
# LOCK must be >= RECOGNISE.
FACE_RECOGNISE_THRESHOLD = 0.45
FACE_LOCK_THRESHOLD = 0.60

# Samples captured per person during enrollment.
# One embedding per face is fragile; averaging several
# across angles is the single biggest accuracy win here.
ENROLL_SAMPLES = 5
ENROLL_MIN_INTERVAL = 0.35


####################################################
# Low light
####################################################

# Auto-enhance frames darker than this before running
# detection. 0-255 mean luminance. Around 60 is a dim
# indoor room; below 30 is genuinely dark.
LOW_LIGHT_AUTO = True
LOW_LIGHT_BRIGHTNESS = 70.0

# Frame rate to drop to in low-light mode. Halving the
# frame rate doubles the time available per exposure --
# that is where the extra light actually comes from.
LOW_LIGHT_FPS = 15


####################################################
# Person following
####################################################

# These are FACE box widths in pixels, not body boxes.
# A face 380px wide means their nose is on the lens.
FOLLOW_FACE_TOO_CLOSE = 160
FOLLOW_FACE_TOO_FAR = 70

# Fraction of frame width treated as "straight ahead".
FOLLOW_DEAD_ZONE = 0.10
FOLLOW_FAST_ZONE = 0.25

# Motors stop if the follow loop stalls this long.
FOLLOW_WATCHDOG_SECONDS = 0.5