from memory.memory import Memory

memory = Memory()


def search_memory(command):

    command = command.lower()

    memories = memory.all_memories()

    for key, value in memories.items():

        readable_key = key.replace("_", " ")

        if readable_key in command:
            return value

    return None