"""
=========================================================
File: mouth.py
Author: Pranjal

Purpose:
Ved's mouth.

Built from parabolic centrelines rather than
pygame.draw.arc. Two reasons:

  1. arc() strokes are constant-width and aliased. The
     concept art's smile is fat in the middle and tapers
     to points at the corners.
  2. arc() angle handling is a trap -- 0..pi draws the
     TOP half of the ellipse, which reads as a frown.
     Parabolas make the direction explicit: positive
     'depth' dips the centre down = smile.
=========================================================
"""

import pygame

from constants import *
from expressions import Expression
from glow import (
    glow_stroke,
    glow_polygon_outline,
    fill_shape,
)


SEGMENTS = 44


####################################################
# Curve builders
####################################################

def smile_curve(cx, cy, half_w, depth, tilt=0.0, segments=SEGMENTS):
    """
    Parabola through (cx-half_w, cy) .. (cx+half_w, cy).

    depth > 0  -> centre dips down  -> smile
    depth < 0  -> centre lifts up   -> frown
    tilt       -> raises one side, for smirks
    """

    points = []

    for i in range(segments + 1):

        t = -1.0 + 2.0 * i / segments

        x = cx + t * half_w
        y = cy + depth * (1.0 - t * t) + tilt * t

        points.append((x, y))

    return points


def taper(peak, ends, segments=SEGMENTS):
    """Thickness profile: fat at the centre, fine at the tips."""

    out = []

    for i in range(segments + 1):

        t = -1.0 + 2.0 * i / segments
        k = (1.0 - t * t) ** 0.55

        out.append(ends + (peak - ends) * k)

    return out


def lens_shape(cx, cy, half_w, top_depth, bottom_depth, segments=SEGMENTS):
    """
    Closed shape between two parabolas -- an open mouth.

    top_depth    how far the upper lip bows (down if > 0)
    bottom_depth how far the lower lip drops
    """

    top = []
    bottom = []

    for i in range(segments + 1):

        t = -1.0 + 2.0 * i / segments

        x = cx + t * half_w
        k = 1.0 - t * t

        top.append((x, cy + top_depth * k))
        bottom.append((x, cy + bottom_depth * k))

    return top + list(reversed(bottom))


class Mouth:

    def __init__(self):

        self.mode = Expression.IDLE.value
        self.speaking_frame = 0

    ###################################################

    def set_mode(self, mode):

        self.mode = mode

    ###################################################

    def set_speaking_frame(self, frame):

        self.speaking_frame = frame

    ###################################################

    @staticmethod
    def _open_mouth(screen, cx, cy, half_w, top_depth, bottom_depth):

        shape = lens_shape(cx, cy, half_w, top_depth, bottom_depth)

        # Inner fill
        fill_shape(screen, MOUTH_INNER, shape)

        # Darker toward the back of the throat
        inner = lens_shape(
            cx,
            cy + (bottom_depth - top_depth) * 0.30,
            half_w * 0.62,
            top_depth * 0.4,
            bottom_depth * 0.55
        )

        fill_shape(screen, MOUTH_INNER_DARK, inner)

        # Glowing rim
        glow_polygon_outline(screen, MOUTH_GLOW, shape, 5.0)

    ###################################################

    def draw(self, screen, y_offset=0):

        cx = MOUTH_X
        cy = MOUTH_Y + y_offset

        colour = MOUTH_GLOW

        # ------------------------------
        # Idle -- wide sweeping smile
        # ------------------------------

        if self.mode == Expression.IDLE.value:

            glow_stroke(
                screen,
                colour,
                smile_curve(cx, cy - 14, 98, 32),
                taper(9.0, 2.5)
            )

        # ------------------------------
        # Happy -- wide, shallow open smile
        # ------------------------------

        elif self.mode == Expression.HAPPY.value:

            self._open_mouth(screen, cx, cy - 18, 68, 2, 50)

        # ------------------------------
        # Listening -- small, attentive, slightly open
        #
        # A closed curve reads as a smile, which is what
        # made this indistinguishable from idle. A small
        # OPEN mouth reads as "I'm taking this in" --
        # narrow, barely parted, no big grin.
        # ------------------------------

        elif self.mode == Expression.LISTENING.value:

            self._open_mouth(screen, cx, cy - 4, 30, -7, 11)

        # ------------------------------
        # Thinking -- pursed, pulled to one side
        #
        # Asymmetry is the whole signal here. A symmetric
        # curve is a smile no matter how shallow you make
        # it; a short stroke shifted off-centre and
        # angled reads as considering something.
        # ------------------------------

        elif self.mode == Expression.THINKING.value:

            glow_stroke(
                screen,
                colour,
                smile_curve(
                    cx + 16, cy - 2,
                    38,
                    6,
                    tilt=-16
                ),
                taper(8.5, 3.0)
            )

        # ------------------------------
        # Speaking -- animated open oval
        # ------------------------------

        elif self.mode == Expression.SPEAKING.value:

            # Minimum opening raised from 14 to 22. At 14
            # the closed end of the animation looked like
            # a slit rather than a mouth, and most frames
            # sit near the bottom of the range.
            open_amt = 22 + self.speaking_frame * 8
            width = 52 - self.speaking_frame * 1.5

            self._open_mouth(
                screen,
                cx,
                cy - open_amt * 0.5,
                width,
                -open_amt * 0.55,
                open_amt * 1.05
            )

        # ------------------------------
        # Surprised -- round O
        # ------------------------------

        elif self.mode == Expression.SURPRISED.value:

            # Wider than tall, or the lens shape collapses
            # into a thin diamond instead of a round O.
            # half_w 25 with depth 26 each way meant the
            # curves met almost immediately.
            self._open_mouth(screen, cx, cy, 38, -30, 30)

        # ------------------------------
        # Sad -- downturned
        # ------------------------------

        elif self.mode == Expression.SAD.value:

            glow_stroke(
                screen,
                colour,
                smile_curve(cx, cy + 16, 80, -26),
                taper(8.0, 2.5)
            )

        # ------------------------------
        # Sleeping -- small resting curve
        # ------------------------------

        elif self.mode == Expression.SLEEPING.value:

            glow_stroke(
                screen,
                colour,
                smile_curve(cx, cy - 6, 48, 12),
                taper(6.0, 2.0)
            )

        # ------------------------------
        # Wink -- cheeky lopsided smile
        # ------------------------------

        elif self.mode == Expression.WINK.value:

            glow_stroke(
                screen,
                colour,
                smile_curve(cx, cy - 10, 84, 26, tilt=-9),
                taper(8.5, 2.5)
            )