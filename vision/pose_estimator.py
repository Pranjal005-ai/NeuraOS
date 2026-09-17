"""
pose_estimator.py

Maintains the estimated pose of Ved.

Pose consists of:
- X position
- Y position
- Heading (rotation)

Author: NeuraOS
"""


class PoseEstimator:

    def __init__(self):

        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0

    # -----------------------------------------
    # Update Pose
    # -----------------------------------------

    def update(self, motion):

        if motion is None:
            return

        self.x += motion["dx"]
        self.y += motion["dy"]
        self.heading += motion["angle"]

    # -----------------------------------------
    # Reset Pose
    # -----------------------------------------

    def reset(self):

        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0

    # -----------------------------------------
    # Current Pose
    # -----------------------------------------

    def get_pose(self):

        return {

            "x": self.x,
            "y": self.y,
            "heading": self.heading

        }


poseEstimator = PoseEstimator()