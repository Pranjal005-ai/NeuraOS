"""
Test Visual Odometry

Press Q to quit.
"""

import cv2

from vision.camera import camera
from vision.feature_detector import featureDetector
from vision.feature_matcher import featureMatcher
from vision.visual_odometry import visualOdometry


prev_frame = None
prev_keypoints = None
prev_descriptors = None


while True:

    frame = camera.get_frame()

    if frame is None:
        continue

    keypoints, descriptors = featureDetector.detect(frame)

    if prev_frame is not None:

        matches = featureMatcher.match(
            prev_descriptors,
            descriptors
        )

        motion = visualOdometry.estimate(
            prev_keypoints,
            keypoints,
            matches
        )

        output = frame.copy()

        if motion:

            cv2.putText(

                output,

                f"dx: {motion['dx']:.2f}",

                (20, 30),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.7,

                (0,255,0),

                2

            )

            cv2.putText(

                output,

                f"dy: {motion['dy']:.2f}",

                (20,60),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.7,

                (0,255,0),

                2

            )

            cv2.putText(

                output,

                f"angle: {motion['angle']:.2f}",

                (20,90),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.7,

                (0,255,0),

                2

            )

            cv2.putText(

                output,

                f"X: {motion['x']:.2f}",

                (20,130),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.7,

                (255,255,0),

                2

            )

            cv2.putText(

                output,

                f"Y: {motion['y']:.2f}",

                (20,165),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.7,

                (255,255,0),

                2

            )

        cv2.imshow(
            "Visual Odometry",
            output
        )

    prev_frame = frame.copy()
    prev_keypoints = keypoints
    prev_descriptors = descriptors

    if cv2.waitKey(1) == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()