"""
=========================================================
File: renderer.py
Author: Pranjal

Purpose:
Renders Ved's animated face.

WHAT CHANGED
------------
The eyelid block now handles WINK. Previously it only
knew about sleeping and blinking, both of which close
BOTH eyes -- so on WINK the mouth and eyebrows changed
while the eyes stayed wide open, and the expression read
as a smirk rather than a wink.
=========================================================
"""

import pygame

from constants import *
from expressions import Expression

from eyes import Eyes
from eyebrows import Eyebrows
from mouth import Mouth

from speech_animator import SpeechAnimator
from idle_animation import IdleAnimation
from eyelids import eyelids


class FaceRenderer:

    ####################################################

    def __init__(self):

        pygame.init()

        self.screen = pygame.display.set_mode(
            (
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            )
        )

        pygame.display.set_caption("Ved AI Face")

        ################################################
        # Face Components
        ################################################

        self.eyes = Eyes()
        self.eyebrows = Eyebrows()
        self.mouth = Mouth()

        ################################################
        # Animation Controllers
        ################################################

        self.idle = IdleAnimation()
        self.speech = SpeechAnimator()

        ################################################

        self.clock = pygame.time.Clock()

    ####################################################

    def clear(self):

        self.screen.fill(BLACK)

    ####################################################

    def render(self, expression):

        ################################################
        # Keep window responsive
        ################################################

        pygame.event.pump()

        ################################################
        # Update animations
        ################################################

        self.idle.update()

        ################################################
        # Background
        ################################################

        self.clear()

        ################################################
        # Eye movement
        ################################################

        eye_x, eye_y = self.idle.eye_offset()

        self.eyes.set_offset(
            eye_x,
            eye_y
        )

        ################################################
        # Gaze
        #
        # Where the eyes POINT is the strongest signal
        # available, and until now nothing used it --
        # which is why listening and thinking looked
        # nearly identical.
        #
        #   thinking  -> looks away and up (recalling)
        #   listening -> locks on, very steady
        #   sad       -> looks down
        #   surprised -> wide and fixed
        ################################################

        if expression == Expression.THINKING:
            self.eyes.set_gaze(-0.75, -0.55, steadiness=0.55)

        elif expression == Expression.LISTENING:
            self.eyes.set_gaze(0.0, 0.0, steadiness=0.85)

        elif expression == Expression.SAD:
            self.eyes.set_gaze(0.0, 0.55, steadiness=0.5)

        elif expression == Expression.SURPRISED:
            self.eyes.set_gaze(0.0, -0.15, steadiness=0.9)

        else:
            self.eyes.set_gaze(0.0, 0.0, steadiness=0.0)

        ################################################
        # Blinking
        #
        # eyelids owns all lid animation, so the eyes
        # themselves never draw their own blink.
        ################################################

        self.eyes.set_blink(False)

        ################################################
        # Breathing
        ################################################

        breath = self.idle.breathing_offset()

        ################################################
        # Current Mode
        ################################################

        mode = expression.value

        self.eyebrows.set_mode(mode)
        self.mouth.set_mode(mode)

        ################################################
        # Speaking Animation
        ################################################

        if expression == Expression.SPEAKING:

            self.speech.start()

            frame = self.speech.update()

            self.mouth.set_speaking_frame(frame)

        else:

            self.speech.stop()

        ################################################
        # Draw Face
        ################################################

        self.eyes.draw(
            self.screen,
            breath
        )

        ################################################
        # Eyelids
        #
        # WINK closes ONE eye; sleeping closes both; the
        # idle blink closes both briefly.
        ################################################

        if expression == Expression.WINK:

            # Ved's right as the VIEWER sees it. Swap to
            # "left" if you'd prefer the other side.
            eyelids.set_wink("right", 1.0)

        elif expression == Expression.SLEEPING:

            eyelids.set_amount(1.0)

        elif self.idle.should_blink():

            eyelids.set_amount(0.85)

        else:

            eyelids.set_amount(0.0)

        eyelids.draw(
            self.screen,
            breath
        )

        self.eyebrows.draw(
            self.screen,
            breath
        )

        self.mouth.draw(
            self.screen,
            breath
        )

        ################################################
        # Sleeping Indicator
        ################################################

        if expression == Expression.SLEEPING:

            font = pygame.font.SysFont(
                "Arial",
                42
            )

            text = font.render(
                "Z z",
                True,
                LIGHT_BLUE
            )

            self.screen.blit(
                text,
                (
                    SCREEN_WIDTH - 140,
                    40
                )
            )

        ################################################
        # Refresh Display
        ################################################

        pygame.display.flip()

        ################################################
        # Maintain 60 FPS
        ################################################

        self.clock.tick(60)

    ####################################################

    def close(self):

        pygame.quit()