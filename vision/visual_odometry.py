"""
visual_odometry.py

Visual Odometry for Project Ved

Estimates camera movement using matched ORB features.

Author: NeuraOS
"""

import cv2
import numpy as np


class VisualOdometry:

    def __init__(self):

        self.total_x = 0.0
        self.total_y = 0.0

    # --------------------------------------------------
    # Estimate Motion
    # --------------------------------------------------

    def estimate(self,
                 keypoints1,
                 keypoints2,
                 matches):

        if len(matches) < 8:
            return None

        pts1 = np.float32(
            [keypoints1[m.queryIdx].pt for m in matches]
        )

        pts2 = np.float32(
            [keypoints2[m.trainIdx].pt for m in matches]
        )

        matrix, mask = cv2.estimateAffinePartial2D(
            pts1,
            pts2
        )

        if matrix is None:
            return None

        dx = matrix[0, 2]
        dy = matrix[1, 2]

        angle = np.degrees(
            np.arctan2(
                matrix[1, 0],
                matrix[0, 0]
            )
        )

        self.total_x += dx
        self.total_y += dy

        return {

            "dx": dx,
            "dy": dy,
            "angle": angle,
            "x": self.total_x,
            "y": self.total_y

        }


visualOdometry = VisualOdometry()