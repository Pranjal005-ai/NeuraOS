"""
path_planner.py

Simple Path Planner for Project Ved.

Generates waypoints between two positions.

Author: NeuraOS
"""

import math


class PathPlanner:

    def __init__(self):

        self.current_path = []

    # -----------------------------------------
    # Create Path
    # -----------------------------------------

    def plan_path(self, start, goal, step_size=1.0):

        self.current_path = []

        dx = goal["x"] - start["x"]
        dy = goal["y"] - start["y"]

        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:

            self.current_path.append(goal)

            return self.current_path

        steps = max(1, int(distance / step_size))

        for i in range(steps + 1):

            t = i / steps

            x = start["x"] + dx * t
            y = start["y"] + dy * t

            self.current_path.append({

                "x": x,
                "y": y

            })

        return self.current_path

    # -----------------------------------------
    # Get Path
    # -----------------------------------------

    def get_path(self):

        return self.current_path

    # -----------------------------------------
    # Next Waypoint
    # -----------------------------------------

    def next_waypoint(self):

        if not self.current_path:

            return None

        return self.current_path.pop(0)

    # -----------------------------------------
    # Clear
    # -----------------------------------------

    def clear(self):

        self.current_path = []


pathPlanner = PathPlanner()