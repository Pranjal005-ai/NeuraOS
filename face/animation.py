"""
=========================================================
File: animation.py
Author: Pranjal

Purpose:
Controls Ved's face animations.
=========================================================
"""

import random
import time


class FaceAnimation:

    def __init__(self):

        self.last_blink = time.time()

        self.next_blink = random.uniform(3, 6)

        self.eye_open = True

    def update(self):
        """
        Call continuously inside the main loop.
        """

        current = time.time()

        # Time to blink?
        if current - self.last_blink >= self.next_blink:

            self.eye_open = False

            # Keep eyes closed briefly
            time.sleep(0.15)

            self.eye_open = True

            self.last_blink = current

            self.next_blink = random.uniform(3, 6)

    def eyes_are_open(self):

        return self.eye_open