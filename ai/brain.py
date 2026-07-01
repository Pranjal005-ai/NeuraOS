"""
Project Ved
Robot Brain
"""

class Brain:

    def process_command(self, command):

        command = command.lower()

        if "forward" in command:
            return "MOVE_FORWARD"

        elif "back" in command:
            return "MOVE_BACKWARD"

        elif "left" in command:
            return "TURN_LEFT"

        elif "right" in command:
            return "TURN_RIGHT"

        elif "stop" in command:
            return "STOP"

        else:
            return "CHAT"