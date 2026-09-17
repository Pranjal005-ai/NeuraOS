"""
Test Feature Matcher

Shows ORB feature matches between consecutive frames.

Press Q to quit.
"""

import cv2

from vision.camera import camera
from vision.feature_detector import featureDetector
from vision.feature_matcher import featureMatcher


previous_frame = None
previous_keypoints = None
previous_descriptors = None


while True:

    frame = camera.get_frame()

    if frame is None:
        continue

    keypoints, descriptors = featureDetector.detect(frame)

    if previous_frame is not None:

        matches = featureMatcher.match(
            previous_descriptors,
            descriptors
        )

        output = cv2.drawMatches(

            previous_frame,
            previous_keypoints,

            frame,
            keypoints,

            matches[:50],

            None,

            flags=2

        )

        cv2.imshow(
            "Feature Matching",
            output
        )

    previous_frame = frame.copy()
    previous_keypoints = keypoints
    previous_descriptors = descriptors

    key = cv2.waitKey(1)

    if key == ord("q"):
        break


camera.release()

cv2.destroyAllWindows()