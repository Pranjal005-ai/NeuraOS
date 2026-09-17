"""
Test Face Detector
"""

import cv2

from face_detector import face_detector
from camera import release_camera

while True:

    frame, faces = face_detector.detect()

    if frame is None:
        continue

    frame = face_detector.draw(
        frame,
        faces
    )

    cv2.imshow(
        "Ved Face Detection",
        frame
    )

    key = cv2.waitKey(1)

    if key == ord("q"):
        break

release_camera()

cv2.destroyAllWindows()