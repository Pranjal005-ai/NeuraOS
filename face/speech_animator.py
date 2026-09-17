"""
=========================================================
File: speech_animator.py
Author: Pranjal

Purpose:
Controls Ved's mouth animation while speaking.
=========================================================
"""

import time
import random


class SpeechAnimator:

    def __init__(self):

        self.speaking = False

        self.last_change = time.time()

        self.interval = 0.08

        self.current_frame = 0

    ####################################################

    def start(self):

        self.speaking = True

        self.last_change = time.time()

    ####################################################

    def stop(self):

        self.speaking = False

        self.current_frame = 0

    ####################################################

    def update(self):

        if not self.speaking:
            return 0

        now = time.time()

        if now - self.last_change >= self.interval:

            self.current_frame = random.randint(1, 4)

            self.last_change = now

        return self.current_frame