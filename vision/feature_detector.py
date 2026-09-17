"""
feature_detector.py

Visual Feature Detector for Project Ved

Uses ORB to detect keypoints and descriptors.

Author: NeuraOS
"""

import cv2


class FeatureDetector:

    def __init__(self):

        # Create ORB detector
        self.detector = cv2.ORB_create(
            nfeatures=1000
        )

    # --------------------------------------------------
    # Detect Features
    # --------------------------------------------------

    def detect(self, frame):
        """
        Detect ORB keypoints and descriptors.
        """

        if frame is None:
            return [], None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        keypoints, descriptors = self.detector.detectAndCompute(
            gray,
            None
        )

        return keypoints, descriptors

    # --------------------------------------------------
    # Draw Features
    # --------------------------------------------------

    def draw(self, frame, keypoints):

        return cv2.drawKeypoints(
            frame,
            keypoints,
            None,
            color=(0, 255, 0),
            flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
        )


# Singleton

featureDetector = FeatureDetector()