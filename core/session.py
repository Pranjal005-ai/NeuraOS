"""
session.py
Stores the current state and conversation history
for Project Ved.
"""

from core.state import RobotState


class Session:

    def __init__(self):

        # -----------------------------
        # Robot State
        # -----------------------------
        self.state = RobotState.SLEEPING

        # -----------------------------
        # Conversation History
        # -----------------------------
        self.chat_history = []

    # ==========================================================
    # Robot State
    # ==========================================================

    def set_state(self, state):
        """
        Change the robot state.
        """

        self.state = state

    def get_state(self):
        """
        Returns the current robot state.
        """

        return self.state

    # ==========================================================
    # Wake / Sleep Helpers
    # ==========================================================

    def wake(self):
        """
        Wake the robot.
        """

        self.set_state(RobotState.LISTENING)

    def sleep(self):
        """
        Put the robot to sleep.
        """

        self.set_state(RobotState.SLEEPING)

    def is_active(self):
        """
        Returns True if robot is awake.
        """

        return self.state != RobotState.SLEEPING

    # ==========================================================
    # Chat History
    # ==========================================================

    def add_message(self, role, content):
        """
        Adds a message to the conversation history.
        """

        self.chat_history.append(
            {
                "role": role,
                "content": content
            }
        )

    def get_history(self):
        """
        Returns a copy of the chat history, so callers can't
        accidentally mutate the session's internal state.
        """

        return self.chat_history.copy()

    def last_message(self):
        """
        Returns the most recent message.
        """

        if not self.chat_history:
            return None

        return self.chat_history[-1]

    def clear_history(self):
        """
        Clears the conversation history.
        """

        self.chat_history.clear()

    # ==========================================================
    # Reset Session
    # ==========================================================

    def reset(self):
        """
        Reset the robot session.
        """

        self.state = RobotState.SLEEPING

        self.clear_history()