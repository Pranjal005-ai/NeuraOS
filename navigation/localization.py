"""
localization.py

Localization for Project Ved.

Determines the robot's current position
using a previously built map.

Author: NeuraOS
"""


import math


class Localization:

    def __init__(self):

        self.current_pose = None
        self.loaded_map = None

    # -----------------------------------------
    # Load Map
    # -----------------------------------------

    def load_map(self, map_data):

        self.loaded_map = map_data

    # -----------------------------------------
    # Update Current Pose
    # -----------------------------------------

    def update_pose(self, pose):

        self.current_pose = pose

    # -----------------------------------------
    # Find Closest Stored Pose
    # -----------------------------------------

    def localize(self):

        if self.loaded_map is None:

            print("No map loaded.")

            return None

        if self.current_pose is None:

            print("Current pose unavailable.")

            return None

        best_frame = None
        minimum_distance = float("inf")

        for frame in self.loaded_map:

            stored_pose = frame["pose"]

            dx = stored_pose["x"] - self.current_pose["x"]
            dy = stored_pose["y"] - self.current_pose["y"]

            distance = math.sqrt(dx * dx + dy * dy)

            if distance < minimum_distance:

                minimum_distance = distance
                best_frame = frame

        return {

            "distance": minimum_distance,

            "frame": best_frame

        }


localization = Localization()