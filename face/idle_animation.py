"""
=========================================================
File: idle_animation.py
Author: Pranjal

Purpose:
Controls Ved's idle behaviour.

Features
---------
• Natural blinking
• Random eye movement
• Breathing offset
=========================================================
"""

import random
import time
import math


class IdleAnimation:

    def __init__(self):

        # -----------------------------
        # Blink
        # -----------------------------

        self.blink = False

        self.last_blink = time.time()

        self.next_blink = random.uniform(3, 6)

        self.blink_duration = 0.12

        # -----------------------------
        # Eye movement
        # -----------------------------

        self.eye_x = 0
        self.eye_y = 0

        self.last_move = time.time()

        self.next_move = random.uniform(2, 4)

        # -----------------------------
        # Breathing
        # -----------------------------

        self.start_time = time.time()

    ####################################################

    def update(self):

        now = time.time()

        # ---------------------------------
        # Blink
        # ---------------------------------

        if not self.blink:

            if now - self.last_blink >= self.next_blink:

                self.blink = True

                self.last_blink = now

        else:

            if now - self.last_blink >= self.blink_duration:

                self.blink = False

                self.last_blink = now

                self.next_blink = random.uniform(3, 6)

        # ---------------------------------
        # Eye Movement
        # ---------------------------------

        if now - self.last_move >= self.next_move:

            self.eye_x = random.randint(-8, 8)

            self.eye_y = random.randint(-5, 5)

            self.last_move = now

            self.next_move = random.uniform(2, 4)

    ####################################################

    def should_blink(self):

        return self.blink

    ####################################################

    def eye_offset(self):

        return self.eye_x, self.eye_y

    ####################################################

    def breathing_offset(self):

        t = time.time() - self.start_time

        return math.sin(t * 1.2) * 2