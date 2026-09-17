"""
mission.py

Defines a robot mission.
"""


class Mission:

    def __init__(self, name):

        self.name = name

        self.actions = []

    def add_action(self, action):

        self.actions.append(action)

    def __repr__(self):

        return f"<Mission {self.name}: {len(self.actions)} actions>"