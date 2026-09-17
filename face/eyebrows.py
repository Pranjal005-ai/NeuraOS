"""
=========================================================
File: eyebrows.py
Author: Pranjal

Purpose:
Ved's eyebrows.

The concept art uses soft, tapered, slightly arched
strokes in near-black — not glowing lines. Each brow is
built as a polygon so it can taper to a point at the
outer end, which is what sells the "drawn" look.

Public API unchanged: set_mode() + draw(screen, y_offset).
=========================================================
"""

import pygame

try:
    from pygame import gfxdraw
    _HAS_GFX = True
except ImportError:
    _HAS_GFX = False

from constants import *
from expressions import Expression


####################################################
# Per-expression shaping
#
#   arch         how curved the brow is
#   inner_raise  px the inner (nose-side) end lifts
#   outer_raise  px the outer (ear-side) end lifts
#   width        half-length of the brow
####################################################

BROW_SHAPES = {

    Expression.IDLE.value: {
        "arch": 15, "inner_raise": 0, "outer_raise": 0
    },

    Expression.HAPPY.value: {
        "arch": 19, "inner_raise": 2, "outer_raise": 9
    },

    # Listening: both brows lifted evenly and held high.
    # Open, attentive, symmetrical -- the opposite of
    # thinking. Previously this was a 7px inner raise,
    # near enough to idle to be invisible.
    Expression.LISTENING.value: {
        "arch": 18, "inner_raise": 14, "outer_raise": 12
    },

    # Thinking: strongly asymmetric. One brow furrowed
    # down and in, the other lifted. This is THE signal
    # for concentration, and it has to be exaggerated to
    # read at all on a small display.
    Expression.THINKING.value: {
        "arch": 8, "inner_raise": 16, "outer_raise": -10,
        "right": {"arch": 20, "inner_raise": 4, "outer_raise": 18}
    },

    Expression.SPEAKING.value: {
        "arch": 15, "inner_raise": 1, "outer_raise": 2
    },

    Expression.SURPRISED.value: {
        "arch": 22, "inner_raise": 20, "outer_raise": 22
    },

    Expression.SAD.value: {
        "arch": 8, "inner_raise": 13, "outer_raise": -10
    },

    Expression.SLEEPING.value: {
        "arch": 7, "inner_raise": -3, "outer_raise": -3, "width": 52
    },

    Expression.WINK.value: {
        "arch": 15, "inner_raise": 0, "outer_raise": 0,
        "right": {"arch": 20, "inner_raise": 14, "outer_raise": 16}
    },
}


class Eyebrows:

    def __init__(self):

        self.mode = Expression.IDLE.value

    ###################################################

    def set_mode(self, mode):

        self.mode = mode

    ###################################################

    @staticmethod
    def _brow_points(
        cx,
        cy,
        half_w,
        arch,
        inner_raise,
        outer_raise,
        thick_inner,
        thick_outer,
        mirror,
        segments=22
    ):
        """
        Build the outline of one brow.

        mirror = +1 for the left brow, -1 for the right.
        't' runs -1 (screen left) .. +1 (screen right);
        's' runs -1 (outer end)   .. +1 (inner end).
        """

        top = []
        bottom = []

        for i in range(segments + 1):

            t = -1.0 + 2.0 * i / segments
            s = t * mirror

            k = (s + 1.0) / 2.0

            raise_px = outer_raise + (inner_raise - outer_raise) * k
            thick = thick_outer + (thick_inner - thick_outer) * k

            x = cx + t * half_w
            y = cy - arch * (1.0 - t * t) - raise_px

            top.append((x, y - thick / 2.0))
            bottom.append((x, y + thick / 2.0))

        return top + list(reversed(bottom))

    ###################################################

    @staticmethod
    def _fill(screen, points, colour):

        pts = [(int(round(p[0])), int(round(p[1]))) for p in points]

        if len(pts) < 3:
            return

        if _HAS_GFX:
            gfxdraw.filled_polygon(screen, pts, colour)
            gfxdraw.aapolygon(screen, pts, colour)
        else:
            pygame.draw.polygon(screen, colour, pts)

    ###################################################

    def _draw_one(self, screen, cx, cy, shape, mirror):

        half_w = shape.get("width", BROW_HALF_WIDTH)

        points = self._brow_points(
            cx,
            cy,
            half_w,
            shape["arch"],
            shape["inner_raise"],
            shape["outer_raise"],
            BROW_THICK_INNER,
            BROW_THICK_OUTER,
            mirror
        )

        self._fill(screen, points, BROW_COLOR)

        # Thin sheen along the upper edge.
        sheen = self._brow_points(
            cx,
            cy,
            half_w,
            shape["arch"],
            shape["inner_raise"] + BROW_THICK_INNER * 0.28,
            shape["outer_raise"] + BROW_THICK_OUTER * 0.28,
            max(1.0, BROW_THICK_INNER * 0.30),
            max(1.0, BROW_THICK_OUTER * 0.30),
            mirror
        )

        self._fill(screen, sheen, BROW_HIGHLIGHT)

    ###################################################

    def draw(self, screen, y_offset=0):

        shape = BROW_SHAPES.get(
            self.mode,
            BROW_SHAPES[Expression.IDLE.value]
        )

        right_shape = dict(shape)
        right_shape.update(shape.get("right", {}))

        y = BROW_Y + y_offset

        self._draw_one(screen, LEFT_EYE_X, y, shape, mirror=1)
        self._draw_one(screen, RIGHT_EYE_X, y, right_shape, mirror=-1)