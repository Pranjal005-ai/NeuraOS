"""
landmark_manager.py

Stores visual landmarks detected by Ved.

Author: NeuraOS
"""


class LandmarkManager:

    def __init__(self):

        self.landmarks = {}
        self.next_id = 1

    # -----------------------------------------
    # Add Landmark
    # -----------------------------------------

    def add_landmark(self, x, y):

        landmark_id = self.next_id

        self.landmarks[landmark_id] = {

            "id": landmark_id,
            "x": x,
            "y": y,
            "observations": 1

        }

        self.next_id += 1

        return landmark_id

    # -----------------------------------------
    # Update Landmark
    # -----------------------------------------

    def update_landmark(self, landmark_id, x, y):

        if landmark_id not in self.landmarks:
            return

        landmark = self.landmarks[landmark_id]

        landmark["x"] = x
        landmark["y"] = y
        landmark["observations"] += 1

    # -----------------------------------------
    # Get Landmark
    # -----------------------------------------

    def get_landmark(self, landmark_id):

        return self.landmarks.get(landmark_id)

    # -----------------------------------------
    # Get All
    # -----------------------------------------

    def get_all(self):

        return self.landmarks

    # -----------------------------------------
    # Reset
    # -----------------------------------------

    def clear(self):

        self.landmarks.clear()

        self.next_id = 1


landmarkManager = LandmarkManager()