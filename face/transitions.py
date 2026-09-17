"""
=========================================================
File: transitions.py

Purpose:
Smoothly interpolate values for facial animations.
=========================================================
"""

import time


class Transition:

    def __init__(self, speed=0.15):

        self.speed = speed

        self.current = 0.0

        self.target = 0.0

    ####################################################

    def set(self, value):

        self.target = value

    ####################################################

    def update(self):

        self.current += (
            self.target - self.current
        ) * self.speed

        return self.current

    ####################################################

    def value(self):

        return self.current