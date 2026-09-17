"""
Test Pose Estimator

Press Q to quit.
"""

import cv2

from vision.camera import camera
from vision.feature_detector import featureDetector
from vision.feature_matcher import featureMatcher
from vision.visual_odometry import visualOdometry
from vision.pose_estimator import poseEstimator


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

        motion = visualOdometry.estimate(
            previous_keypoints,
            keypoints,
            matches
        )

        poseEstimator.update(motion)

        pose = poseEstimator.get_pose()

        output = frame.copy()

        cv2.putText(
            output,
            f"X : {pose['x']:.2f}",
            (20,40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0,255,0),
            2
        )

        cv2.putText(
            output,
            f"Y : {pose['y']:.2f}",
            (20,80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0,255,0),
            2
        )

        cv2.putText(
            output,
            f"Heading : {pose['heading']:.2f}",
            (20,120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255,255,0),
            2
        )

        cv2.imshow(
            "Pose Estimation",
            output
        )

    previous_frame = frame.copy()
    previous_keypoints = keypoints
    previous_descriptors = descriptors

    if cv2.waitKey(1) == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()