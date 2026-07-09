"""
brain.py
Decision engine for Project Ved
"""


class Brain:

    def process_command(self, command):

        command = command.lower()

        # ========================
        # MOVEMENT
        # ========================

        if any(word in command for word in [
            "forward",
            "go forward",
            "move forward",
            "आगे"
        ]):
            return "MOVE_FORWARD"

        if any(word in command for word in [
            "back",
            "backward",
            "पीछे"
        ]):
            return "MOVE_BACKWARD"

        if any(word in command for word in [
            "left",
            "बाएं"
        ]):
            return "TURN_LEFT"

        if any(word in command for word in [
            "right",
            "दाएं"
        ]):
            return "TURN_RIGHT"

        if any(word in command for word in [
            "stop",
            "रुको"
        ]):
            return "STOP"

        # ========================
        # VISION
        # ========================

        if any(word in command for word in [

            "what do you see",
            "look around",
            "describe",
            "camera",
            "who is in front"

        ]):

            return "VISION"

        # ========================
        # MEMORY
        # ========================

        if "remember" in command:

            return "MEMORY_SAVE"

        if "what do you remember" in command:

            return "MEMORY_READ"

        # ========================
        # DEFAULT
        # ========================

        return "CHAT"