"""
=========================================================
camera_calibration.py

Computes the camera matrix and distortion coefficients
for the Pi Camera Module.

Run from the PROJECT ROOT:
    python3 -m vision.camera_calibration

Author: Pranjal

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. object_points / image_points are reset at the start
   of calibrate(). They used to accumulate across calls,
   so calling calibrate() twice in one session silently
   corrupted the result.
2. Paths resolve from the project, not the cwd.
3. Reports reprojection error -- without it you have no
   idea whether a calibration is good. Under 0.5 is fine,
   over 1.0 means recapture.
4. Added a live capture helper, since collecting the
   chessboard images was previously left as an exercise.
=========================================================
"""

import glob
import pickle

import cv2
import numpy as np

from vision.config import CALIBRATION_FILE, VISION_DIR


CALIBRATION_DIR = VISION_DIR / "calibration"


class CameraCalibration:

    def __init__(self, rows=6, cols=9):

        # Inside corners, not squares.
        self.rows = rows
        self.cols = cols

        self.criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            30,
            0.001
        )

        self.object_points = []
        self.image_points = []

        objp = np.zeros((rows * cols, 3), np.float32)

        objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)

        self.objp = objp

    ##################################################

    def reset(self):

        self.object_points = []
        self.image_points = []

    ##################################################

    def calibrate(self, image_folder=None, show=True):

        # Fresh state every run.
        self.reset()

        pattern = str(
            image_folder or (CALIBRATION_DIR / "*.jpg")
        )

        images = sorted(glob.glob(pattern))

        if not images:
            print(f"No calibration images at {pattern}")
            return False

        print(f"Found {len(images)} images.")

        gray = None
        used = 0

        for path in images:

            frame = cv2.imread(path)

            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            found, corners = cv2.findChessboardCorners(
                gray, (self.cols, self.rows), None
            )

            if not found:
                print(f"  no chessboard: {path}")
                continue

            self.object_points.append(self.objp)

            refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1), self.criteria
            )

            self.image_points.append(refined)

            used += 1

            if show:
                cv2.drawChessboardCorners(
                    frame, (self.cols, self.rows), refined, found
                )
                cv2.imshow("Calibration", frame)
                cv2.waitKey(200)

        if show:
            cv2.destroyAllWindows()

        if used < 5:
            print(
                f"Only {used} usable images. "
                "Capture at least 10 from varied angles."
            )
            return False

        ok, matrix, distortion, rvecs, tvecs = cv2.calibrateCamera(
            self.object_points,
            self.image_points,
            gray.shape[::-1],
            None,
            None
        )

        if not ok:
            print("Calibration failed.")
            return False

        ##############################################
        # Reprojection error
        ##############################################

        total = 0.0

        for i in range(len(self.object_points)):

            projected, _ = cv2.projectPoints(
                self.object_points[i],
                rvecs[i], tvecs[i], matrix, distortion
            )

            error = cv2.norm(
                self.image_points[i], projected, cv2.NORM_L2
            ) / len(projected)

            total += error

        mean_error = total / len(self.object_points)

        ##############################################
        # Save
        ##############################################

        CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(CALIBRATION_FILE, "wb") as f:
            pickle.dump(
                {
                    "camera_matrix": matrix,
                    "distortion": distortion,
                    "image_size": gray.shape[::-1],
                    "reprojection_error": mean_error,
                    "images_used": used,
                },
                f
            )

        print()
        print("=" * 52)
        print("CAMERA CALIBRATION COMPLETE")
        print("=" * 52)
        print(f"Images used         : {used}")
        print(f"Reprojection error  : {mean_error:.4f}")

        if mean_error > 1.0:
            print("  ^ too high. Recapture from more angles.")
        elif mean_error < 0.5:
            print("  ^ good.")

        print(f"\nSaved to {CALIBRATION_FILE}")
        print("\nCamera matrix:")
        print(matrix)
        print("\nDistortion:")
        print(distortion)

        return True

    ##################################################

    def capture_images(self, count=15):
        """
        Grab chessboard shots from the live camera.

        Hold a printed chessboard at varied angles and
        distances -- corners and tilts matter more than
        head-on shots.
        """

        from vision.camera import get_camera, release_camera

        CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)

        cam = get_camera()

        if cam.wait_for_frame() is None:
            print("No frames from camera.")
            return 0

        print(f"Capturing {count} images.")
        print("SPACE = capture (only when corners show)")
        print("ESC   = done")

        saved = 0

        try:
            while saved < count:

                frame = cam.get_frame()

                if frame is None:
                    continue

                preview = frame.copy()

                gray = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)

                found, corners = cv2.findChessboardCorners(
                    gray, (self.cols, self.rows), None
                )

                if found:
                    cv2.drawChessboardCorners(
                        preview, (self.cols, self.rows),
                        corners, found
                    )

                cv2.putText(
                    preview,
                    f"{saved}/{count}  "
                    f"{'READY' if found else 'no board'}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0) if found else (0, 0, 255), 2
                )

                cv2.imshow("Capture Calibration", preview)

                key = cv2.waitKey(1) & 0xFF

                if key == 27:
                    break

                if key == 32 and found:

                    path = CALIBRATION_DIR / f"calib_{saved:02d}.jpg"

                    cv2.imwrite(str(path), frame)

                    saved += 1

                    print(f"  saved {path.name}")

        finally:
            cv2.destroyAllWindows()
            release_camera()

        return saved


####################################################
# Lazy singleton
####################################################

_calibration = None


def get_calibration():

    global _calibration

    if _calibration is None:
        _calibration = CameraCalibration()

    return _calibration


def load_calibration():
    """
    Returns the saved dict, or None if not calibrated.
    """

    if not CALIBRATION_FILE.exists():
        return None

    with open(CALIBRATION_FILE, "rb") as f:
        return pickle.load(f)


####################################################

if __name__ == "__main__":

    calib = get_calibration()

    print("1) Capture chessboard images")
    print("2) Calibrate from saved images")

    choice = input("\nChoice [1/2]: ").strip()

    if choice == "1":
        calib.capture_images()
    else:
        calib.calibrate()