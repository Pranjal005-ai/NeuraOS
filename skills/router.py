"""
Router for Project Ved
"""

from skills.greetings import greet
from skills.about import about
from skills.time_skill import current_time
from skills.vision import see


def run(command):

    command = command.lower()

    if command in ["hi", "hello", "namaste"]:
        return greet()

    if "who are you" in command:
        return about()

    if "time" in command:
        return current_time()

    if (
        "what do you see" in command
        or "look around" in command
        or "describe this" in command
        or "who is in front of you" in command
    ):
        return see()

    return None