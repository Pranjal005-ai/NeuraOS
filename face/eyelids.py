"""
=========================================================
File: eyelids.py
Author: Pranjal

Purpose:
Animated eyelids for Ved.

WHAT CHANGED
------------
1. PER-EYE CONTROL. set_amount() set self.left and
   self.right to the same value, and draw() then used
   self.left for BOTH rectangles -- so self.right was
   never read at all. The class could not close one eye,
   which is why winking did nothing.

   Now: set_amount() closes both (blinking, sleeping),
   set_eye() closes one (winking).

2. A LID LINE. A plain black rectangle erases the eye and
   leaves a hole. Real closed eyes show a lid edge --
   a gentle upward curve, which is what makes a wink read
   as playful rather than as a rendering glitch.
=========================================================
"""

import math

import pygame

from constants import *


class Eyelids:

    def __init__(self):

        self.left = 0.0
        self.right = 0.0

    ##################################################

    def set_amount(self, amount):
        """Close both eyes by the same amount."""

        amount = max(0.0, min(1.0, amount))

        self.left = amount
        self.right = amount

    ##################################################

    def set_eye(self, side, amount):
        """
        Close ONE eye.

        side: "left" or "right", as the viewer sees it.
        """

        amount = max(0.0, min(1.0, amount))

        if side == "left":
            self.left = amount
        elif side == "right":
            self.right = amount

    ##################################################

    def set_wink(self, side, amount=1.0):
        """
        Close one eye, open the other.
        side=None reopens both.
        """

        if side is None:
            self.left = 0.0
            self.right = 0.0
            return

        self.left = amount if side == "left" else 0.0
        self.right = amount if side == "right" else 0.0

    ##################################################

    def _draw_one(self, screen, x, y, amount):

        if amount <= 0.01:
            return

        radius = EYE_RADIUS

        # The lid sweeps down from above the eye.
        h = int(radius * 2 * amount)

        pygame.draw.rect(
            screen,
            BLACK,
            (
                x - radius - 2,
                y - radius - 2,
                radius * 2 + 4,
                h
            )
        )

        ##############################################
        # Lid edge
        #
        # Only once the eye is mostly shut. Drawing it
        # during a half-blink puts a line across the
        # middle of an open eye, which looks broken.
        ##############################################

        if amount < 0.75:
            return

        lid_y = y - radius + h

        span = radius - 6

        # A slight upward curve -- the ^_^ shape. A flat
        # line reads as asleep or switched off.
        pygame.draw.arc(
            screen,
            RIM_LIGHT,
            (x - span, lid_y - 16, span * 2, 32),
            0.35,
            math.pi - 0.35,
            5
        )

    ##################################################

    def draw(self, screen, y_offset=0):

        y = EYE_Y + y_offset

        self._draw_one(screen, LEFT_EYE_X, y, self.left)
        self._draw_one(screen, RIGHT_EYE_X, y, self.right)


eyelids = Eyelids()