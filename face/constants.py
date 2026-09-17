"""
=========================================================
File: constants.py
Author: Pranjal

Purpose:
Ved Face constants -- palette + geometry.
Tuned to match the VED AI FACE V2 concept art.
=========================================================
"""

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

FPS = 60

# ----------------------------------------------------
# Base
# ----------------------------------------------------

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# ----------------------------------------------------
# Eye palette
# ----------------------------------------------------

# Thin metallic rim around the eyeball
RIM_LIGHT = (188, 196, 210)
RIM_DARK = (74, 80, 94)

# Iris
IRIS_LIGHT = (26, 110, 245)
IRIS_DARK = (8, 44, 138)

# Pupil
PUPIL_COLOR = (6, 8, 14)

# Halo behind the eye
EYE_GLOW = (18, 82, 200)

# ----------------------------------------------------
# Eyebrow palette (dark, NOT glowing -- see the mockup)
# ----------------------------------------------------

BROW_COLOR = (34, 38, 46)
BROW_HIGHLIGHT = (78, 86, 100)

# ----------------------------------------------------
# Mouth palette
# ----------------------------------------------------

MOUTH_GLOW = (0, 190, 255)
MOUTH_INNER = (150, 28, 38)
MOUTH_INNER_DARK = (86, 14, 22)

# ----------------------------------------------------
# Legacy names (older modules still import these)
# ----------------------------------------------------

CYAN = (0, 255, 255)
LIGHT_BLUE = (0, 190, 255)
BLUE = (30, 120, 255)
DARK_BLUE = (10, 52, 150)

# ----------------------------------------------------
# Eye geometry
# ----------------------------------------------------

LEFT_EYE_X = 272
RIGHT_EYE_X = 528
EYE_Y = 196

EYE_RADIUS = 50
RIM_THICKNESS = 6
PUPIL_RADIUS = 28
HIGHLIGHT_RADIUS = 7

IRIS_RADIUS = EYE_RADIUS - RIM_THICKNESS

# Halo size, as a multiple of EYE_RADIUS
EYE_GLOW_SCALE = 1.75
EYE_GLOW_INTENSITY = 0.34

# How far the pupil may wander from centre
PUPIL_TRAVEL = 8

# ----------------------------------------------------
# Eyebrow geometry
# ----------------------------------------------------

BROW_Y = EYE_Y - 88
BROW_HALF_WIDTH = 62
BROW_ARCH = 14
BROW_THICK_INNER = 6
BROW_THICK_OUTER = 13

# ----------------------------------------------------
# Mouth geometry
# ----------------------------------------------------

MOUTH_X = SCREEN_WIDTH // 2
MOUTH_Y = 344
MOUTH_WIDTH = 170
MOUTH_HEIGHT = 50