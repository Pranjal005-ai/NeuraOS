"""
=========================================================
File: effects.py
Author: Pranjal

Purpose:
Visual effects for Ved.
- Eye glow
- Breathing glow
- Screen vignette
=========================================================
"""

import pygame

from constants import *


class Effects:

    def __init__(self):

        pass

    ####################################################

    def eye_glow(
        self,
        screen,
        x,
        y,
        radius
    ):

        for i in range(6):

            alpha = 35 - (i * 5)

            glow = pygame.Surface(
                (
                    radius * 4,
                    radius * 4
                ),
                pygame.SRCALPHA
            )

            pygame.draw.circle(
                glow,
                (
                    0,
                    255,
                    255,
                    alpha
                ),
                (
                    radius * 2,
                    radius * 2
                ),
                radius + i * 8
            )

            screen.blit(
                glow,
                (
                    x - radius * 2,
                    y - radius * 2
                )
            )

    ####################################################

    def vignette(self, screen):

        overlay = pygame.Surface(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            ),
            pygame.SRCALPHA
        )

        pygame.draw.rect(
            overlay,
            (
                0,
                0,
                0,
                35
            ),
            overlay.get_rect(),
            80
        )

        screen.blit(
            overlay,
            (0, 0)
        )


effects = Effects()