import re

def parse_memory(command):

    command = command.lower()

    if "remember" not in command:
        return None

    text = command.replace("remember", "").strip()

    if " is " in text:

        key, value = text.split(" is ", 1)

        key = key.strip().replace(" ", "_")
        value = value.strip()

        return key, value

    return None