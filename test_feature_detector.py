"""
Test ORB Feature Detector
"""

import cv2

from vision.camera import camera
from vision.feature_detector import featureDetector

while True:

    frame = camera.get_frame()

    if frame is None:
        continue

    keypoints, descriptors = featureDetector.detect(frame)

    output = featureDetector.draw(
        frame,
        keypoints
    )

    cv2.imshow(
        "ORB Feature Detector",
        output
    )

    key = cv2.waitKey(1)

    if key == ord("q"):
        break

camera.release()

cv2.destroyAllWindows()