"""
map_builder.py

Map Builder for Project Ved

Stores the robot pose together with visual landmarks.

Author: NeuraOS
"""


class MapBuilder:

    def __init__(self):

        self.map_data = []

    # -----------------------------------------
    # Add Frame
    # -----------------------------------------

    def add_frame(self, pose, landmarks):

        self.map_data.append({

            "pose": pose.copy(),

            "landmarks": landmarks.copy()

        })

    # -----------------------------------------
    # Total Frames
    # -----------------------------------------

    def frame_count(self):

        return len(self.map_data)

    # -----------------------------------------
    # Get Map
    # -----------------------------------------

    def get_map(self):

        return self.map_data

    # -----------------------------------------
    # Reset
    # -----------------------------------------

    def clear(self):

        self.map_data = []


mapBuilder = MapBuilder()