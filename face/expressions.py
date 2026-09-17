"""
=========================================================
File: expressions.py
Author: Pranjal

Purpose:
Stores all facial expressions used by Ved.
=========================================================
"""

from enum import Enum


class Expression(Enum):
    IDLE = "idle"
    HAPPY = "happy"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    SURPRISED = "surprised"
    SAD = "sad"
    SLEEPING = "sleeping"
    WINK = "wink"


class FaceState:
    """
    Keeps track of Ved's current facial expression.
    """

    def __init__(self):
        self.current = Expression.IDLE

    def set_expression(self, expression: Expression):
        """
        Change Ved's current expression.
        """

        self.current = expression
        print(f"[FACE] Expression -> {expression.value}")

    def get_expression(self):
        """
        Return the current expression.
        """

        return self.current