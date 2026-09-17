"""
=========================================================
qr_scanner.py

QR code scanning.

Author: Pranjal

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. scan(frame) takes a frame argument instead of calling
   get_frame() internally.
2. Added detectAndDecodeMulti, so Ved can see several
   waypoint markers at once and pick the closest -- with
   single-code detection it locks onto an arbitrary one.
3. Returns the box in plain (x1,y1,x2,y2) form like every
   other vision module, rather than raw corner points.
=========================================================
"""

import cv2
import numpy as np


class QRScanner:

    def __init__(self):

        self.detector = cv2.QRCodeDetector()

    ##################################################

    @staticmethod
    def _box(points):

        pts = np.asarray(points).reshape(-1, 2)

        xs = pts[:, 0]
        ys = pts[:, 1]

        return (
            int(xs.min()), int(ys.min()),
            int(xs.max()), int(ys.max())
        )

    ##################################################

    def scan(self, frame):
        """
        Closest (largest) QR code, or None.

        Returns {"text", "box", "area"}.
        """

        codes = self.scan_all(frame)

        return codes[0] if codes else None

    ##################################################

    def scan_all(self, frame):
        """
        Every QR code in the frame, largest first.
        """

        if frame is None:
            return []

        try:
            ok, texts, points, _ = (
                self.detector.detectAndDecodeMulti(frame)
            )
        except cv2.error:
            return []

        if not ok or points is None:
            return []

        codes = []

        for text, corner in zip(texts, points):

            if not text:
                continue

            x1, y1, x2, y2 = self._box(corner)

            codes.append(
                {
                    "text": text,
                    "box": (x1, y1, x2, y2),
                    "area": (x2 - x1) * (y2 - y1),
                }
            )

        codes.sort(key=lambda c: c["area"], reverse=True)

        return codes

    ##################################################

    def draw(self, frame, codes):

        if isinstance(codes, dict):
            codes = [codes]

        for code in codes:

            x1, y1, x2, y2 = code["box"]

            cv2.rectangle(
                frame, (x1, y1), (x2, y2), (0, 255, 255), 2
            )

            cv2.putText(
                frame,
                code["text"],
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )

        return frame


####################################################
# Lazy singleton
####################################################

_scanner = None


def get_scanner():

    global _scanner

    if _scanner is None:
        _scanner = QRScanner()

    return _scanner


def scan(frame):

    return get_scanner().scan(frame)


def scan_all(frame):

    return get_scanner().scan_all(frame)


####################################################

if __name__ == "__main__":

    from vision.camera import get_camera, release_camera

    scanner = get_scanner()
    cam = get_camera()

    if cam.wait_for_frame() is None:
        print("No frames from camera.")
    else:
        print("Scanning -- press Q to quit")

        seen = None

        try:
            while True:

                frame = cam.get_frame()

                if frame is None:
                    continue

                codes = scanner.scan_all(frame)

                scanner.draw(frame, codes)

                if codes and codes[0]["text"] != seen:
                    seen = codes[0]["text"]
                    print(f"[QR] {seen}")

                cv2.imshow("Ved QR Scanner", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            cv2.destroyAllWindows()
            release_camera()