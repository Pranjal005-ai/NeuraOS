"""
=========================================================
File: eyes.py
Author: Pranjal

Purpose:
Ved's eyes, matching the V2 concept art.

Layer order (back to front):
    1. soft radial halo
    2. metallic rim ring
    3. iris, faked vertical gradient
    4. pupil
    5. specular highlights

Public API unchanged -- drop-in replacement.
=========================================================
"""

import math

import pygame

from constants import *
from glow import draw_radial_glow


class Eyes:

    ####################################################

    def __init__(self):

        self.left_pupil_x = LEFT_EYE_X
        self.right_pupil_x = RIGHT_EYE_X

        self.left_pupil_y = EYE_Y
        self.right_pupil_y = EYE_Y

        self.offset_x = 0
        self.offset_y = 0

        # Deliberate gaze direction, on top of the idle
        # drift. This is what separates "thinking" (looking
        # away, up) from "listening" (looking straight at
        # you). Without it both expressions rely on the
        # mouth alone and read almost identically.
        self.gaze_x = 0.0
        self.gaze_y = 0.0

        # Gaze eases toward its target rather than
        # snapping -- eyes that teleport look mechanical.
        self.target_gaze_x = 0.0
        self.target_gaze_y = 0.0

        # How much the idle wander is suppressed. When
        # concentrating, eyes are steadier.
        self.steadiness = 0.0

        self.blink = False

        # Per-eye lids, used for winking.
        self.closed_left = False
        self.closed_right = False

    ####################################################

    def set_gaze(self, x=0.0, y=0.0, steadiness=0.0):
        """
        Point the eyes somewhere.

        x: -1 hard left .. +1 hard right
        y: -1 up .. +1 down
        steadiness: 0 normal wander .. 1 completely still
        """

        self.target_gaze_x = max(-1.0, min(1.0, x))
        self.target_gaze_y = max(-1.0, min(1.0, y))

        self.steadiness = max(0.0, min(1.0, steadiness))

    ####################################################

    def set_blink(self, blink):

        self.blink = blink

    ####################################################

    def set_wink(self, side=None):
        """
        side = "left", "right", or None to reopen both.

        "right" means Ved's right eye as the viewer sees
        it, i.e. the one drawn at RIGHT_EYE_X.
        """

        self.closed_left = (side == "left")
        self.closed_right = (side == "right")

    ####################################################

    def set_offset(self, x, y):

        self.offset_x = x
        self.offset_y = y

    ####################################################

    def move(self, dx=0, dy=0):

        # Never let the pupil escape the iris.
        dist = math.hypot(dx, dy)

        if dist > PUPIL_TRAVEL:
            dx = dx * PUPIL_TRAVEL / dist
            dy = dy * PUPIL_TRAVEL / dist

        self.left_pupil_x = LEFT_EYE_X + dx
        self.left_pupil_y = EYE_Y + dy

        self.right_pupil_x = RIGHT_EYE_X + dx
        self.right_pupil_y = EYE_Y + dy

    ####################################################

    def idle_animation(self):

        t = pygame.time.get_ticks() / 1000.0

        ################################################
        # Ease the gaze toward its target
        ################################################

        ease = 0.12

        self.gaze_x += (self.target_gaze_x - self.gaze_x) * ease
        self.gaze_y += (self.target_gaze_y - self.gaze_y) * ease

        ################################################
        # Idle wander, suppressed when concentrating
        ################################################

        wander = 1.0 - self.steadiness

        dx = math.sin(t * 0.8) * 3 * wander
        dy = math.cos(t * 0.6) * 2 * wander

        ################################################
        # Deliberate gaze, scaled to the travel limit
        ################################################

        dx += self.gaze_x * PUPIL_TRAVEL
        dy += self.gaze_y * PUPIL_TRAVEL

        self.move(
            dx + self.offset_x,
            dy + self.offset_y
        )

    ####################################################
    # Fake a vertical gradient using stacked circles.
    # More steps = less visible banding.
    ####################################################

    @staticmethod
    def _gradient_ball(
        screen,
        center,
        radius,
        top_color,
        bottom_color,
        steps=18
    ):

        cx, cy = int(center[0]), int(center[1])

        for i in range(steps):

            k = i / float(steps - 1)

            r = int(round(radius * (1.0 - k * 0.5)))

            colour = (
                int(bottom_color[0] + (top_color[0] - bottom_color[0]) * k),
                int(bottom_color[1] + (top_color[1] - bottom_color[1]) * k),
                int(bottom_color[2] + (top_color[2] - bottom_color[2]) * k)
            )

            # Drift upward so the top stays brighter.
            oy = int(round(-radius * 0.16 * k))

            pygame.draw.circle(screen, colour, (cx, cy + oy), max(1, r))

    ####################################################

    def draw_eye(self, screen, x, y, pupil_x, pupil_y, closed=False):

        x = int(x)
        y = int(y)

        ################################################
        # 1. Halo
        ################################################

        draw_radial_glow(
            screen,
            EYE_GLOW,
            (x, y),
            int(EYE_RADIUS * EYE_GLOW_SCALE),
            intensity=EYE_GLOW_INTENSITY
        )

        ################################################
        # 2. Metallic rim
        ################################################

        # Dark base, then a lighter ring nudged up:
        # reads as a lit rim with shadow underneath.
        pygame.draw.circle(screen, RIM_DARK, (x, y), EYE_RADIUS)
        pygame.draw.circle(screen, RIM_LIGHT, (x, y - 2), EYE_RADIUS - 1)

        ################################################
        # 3. Closed lid -- blink or wink, skip the rest
        ################################################

        if self.blink or closed:

            pygame.draw.circle(screen, BLACK, (x, y), EYE_RADIUS - 1)

            # A gentle upward curve reads much friendlier
            # than a flat line -- this is the ^_^ shape.
            span = EYE_RADIUS - 6

            pygame.draw.arc(
                screen,
                RIM_LIGHT,
                (x - span, y - 14, span * 2, 34),
                0.30,
                math.pi - 0.30,
                6
            )

            return

        ################################################
        # 4. Iris
        ################################################

        self._gradient_ball(
            screen,
            (x, y),
            IRIS_RADIUS,
            IRIS_LIGHT,
            IRIS_DARK
        )

        ################################################
        # 5. Pupil
        ################################################

        px = int(pupil_x)
        py = int(pupil_y)

        pygame.draw.circle(screen, PUPIL_COLOR, (px, py), PUPIL_RADIUS)

        ################################################
        # 6. Highlights
        ################################################

        pygame.draw.circle(
            screen,
            WHITE,
            (px - int(PUPIL_RADIUS * 0.38), py - int(PUPIL_RADIUS * 0.38)),
            HIGHLIGHT_RADIUS
        )

        pygame.draw.circle(
            screen,
            (120, 150, 190),
            (px + int(PUPIL_RADIUS * 0.42), py + int(PUPIL_RADIUS * 0.45)),
            max(2, HIGHLIGHT_RADIUS // 3)
        )

    ####################################################

    def draw(self, screen, y_offset=0):

        self.idle_animation()

        self.draw_eye(
            screen,
            LEFT_EYE_X,
            EYE_Y + y_offset,
            self.left_pupil_x,
            self.left_pupil_y + y_offset,
            closed=self.closed_left
        )

        self.draw_eye(
            screen,
            RIGHT_EYE_X,
            EYE_Y + y_offset,
            self.right_pupil_x,
            self.right_pupil_y + y_offset,
            closed=self.closed_right
        )