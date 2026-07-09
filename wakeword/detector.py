WAKE_WORDS = [
     "ved",
        "wait",
        "wet",
        "bed",
        "hello ved",
        "hi ved",
        "namaste ved",
        "vidhayak",
        "vet"
]


def is_awake(command):

    command = command.lower()

    for wake in WAKE_WORDS:

        if wake in command:
            return True

    return False