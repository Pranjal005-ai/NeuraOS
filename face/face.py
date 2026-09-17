"""
=========================================================
File: face.py
Author: Pranjal

Purpose:
Main controller for Ved's facial expressions.
=========================================================
"""

from expressions import FaceState, Expression


class VedFace:
    """
    Main interface for controlling Ved's face.
    """

    def __init__(self):
        self.state = FaceState()

    def idle(self):
        self.state.set_expression(Expression.IDLE)

    def happy(self):
        self.state.set_expression(Expression.HAPPY)

    def listening(self):
        self.state.set_expression(Expression.LISTENING)

    def thinking(self):
        self.state.set_expression(Expression.THINKING)

    def speaking(self):
        self.state.set_expression(Expression.SPEAKING)

    def surprised(self):
        self.state.set_expression(Expression.SURPRISED)

    def sad(self):
        self.state.set_expression(Expression.SAD)

    def sleeping(self):
        self.state.set_expression(Expression.SLEEPING)

    def wink(self):
        self.state.set_expression(Expression.WINK)

    def current_expression(self):
        """
        Returns the current expression.
        """

        return self.state.get_expression()