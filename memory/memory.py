import json
import os

MEMORY_FILE = "memory/user_memory.json"


class Memory:

    def __init__(self):

        if not os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "w") as f:
                json.dump({}, f)

    def load(self):

        with open(MEMORY_FILE, "r") as f:
            return json.load(f)

    def save(self, data):

        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def remember(self, key, value):

        data = self.load()

        data[key] = value

        self.save(data)

    def recall(self, key):

        data = self.load()

        return data.get(key)

    def forget(self, key):

        data = self.load()

        if key in data:

            del data[key]

            self.save(data)

    def all_memories(self):

        return self.load()