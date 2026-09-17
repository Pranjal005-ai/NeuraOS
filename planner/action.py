"""
action.py

Represents one robot action.
"""


class Action:

    def __init__(self, action_type, target=None, data=None):

        self.action_type = action_type

        self.target = target

        self.data = data

    def __repr__(self):

        return f"{self.action_type} -> {self.target}"