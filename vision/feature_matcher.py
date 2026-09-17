"""
feature_matcher.py

Visual Feature Matcher

Matches ORB features between two frames.

Author: NeuraOS
"""

import cv2


class FeatureMatcher:

    def __init__(self):

        # Hamming distance works with ORB descriptors
        self.matcher = cv2.BFMatcher(
            cv2.NORM_HAMMING,
            crossCheck=True
        )

    # --------------------------------------------------
    # Match descriptors
    # --------------------------------------------------

    def match(self, desc1, desc2):

        if desc1 is None or desc2 is None:
            return []

        matches = self.matcher.match(
            desc1,
            desc2
        )

        # Sort best matches first
        matches = sorted(matches, key=lambda x: x.distance)

        return matches


# Singleton

featureMatcher = FeatureMatcher()