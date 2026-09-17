"""
=========================================================
emotion_engine.py

Controls Ved's emotions.
=========================================================
"""

from expressions import Expression


class EmotionEngine:

    def __init__(self):

        self.expression = Expression.IDLE

    ################################################

    def set(self, expression):

        self.expression = expression

    ################################################

    def get(self):

        return self.expression

    ################################################

    def is_happy(self):

        return self.expression == Expression.HAPPY

    ################################################

    def is_thinking(self):

        return self.expression == Expression.THINKING

    ################################################

    def is_listening(self):

        return self.expression == Expression.LISTENING

    ################################################

    def is_speaking(self):

        return self.expression == Expression.SPEAKING

    ################################################

    def is_sleeping(self):

        return self.expression == Expression.SLEEPING