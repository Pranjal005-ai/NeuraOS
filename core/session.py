"""
session.py
Stores the current state of the robot.
"""

from core.state import RobotState


class Session:

    def __init__(self):

        # Current robot state
        self.state = RobotState.SLEEPING

        # Conversation memory (optional)
        self.chat_history = []

    # -----------------------------
    # Robot State
    # -----------------------------

    def set_state(self, state):

        self.state = state

    def get_state(self):

        return self.state

    # -----------------------------
    # Chat History
    # -----------------------------

    def add_message(self, role, content):

        self.chat_history.append(
            {
                "role": role,
                "content": content
            }
        )

    def get_history(self):

        return self.chat_history

    def clear_history(self):

        self.chat_history = []