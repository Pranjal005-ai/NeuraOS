"""
map.py

Simple map storage.

Later this will contain
LiDAR-generated maps.
"""


class RobotMap:

    def __init__(self):

        self.locations = {}

    def add_location(self, name):

        self.locations[name] = True

    def exists(self, name):

        return name in self.locations


robot_map = RobotMap()