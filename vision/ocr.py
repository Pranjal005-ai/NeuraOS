"""
=========================================================
ocr.py

Optical Character Recognition.

Author: Pranjal

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. LAZY. `ocr = OCR()` at module scope was the single
   worst import in the project: EasyOCR loads ~500MB of
   models AND DOWNLOADS them on first construction. Any
   import chain reaching this file blocked on the
   network at startup.
2. read(frame) takes a frame argument. It used to grab
   its own, so OCR ran on a different moment than
   everything else in the same tick.
3. Returns structured results with confidence, not just
   concatenated text -- you need confidence to decide
   whether Ved should say "I think that says..." or
   admit it cannot read the sign.

PERFORMANCE WARNING
-------------------
EasyOCR takes ~5-15s per frame on a Pi 5. This is an
ON-DEMAND feature ("Ved, read this"), never a loop.
=========================================================
"""

import cv2


LANGUAGES = ["en", "hi"]

MIN_CONFIDENCE = 0.35


class OCR:

    def __init__(self, languages=None):

        import easyocr

        self.languages = languages or LANGUAGES

        print(f"[OCR] Loading EasyOCR {self.languages}...")
        print("[OCR] First run downloads models -- be patient.")

        self.reader = easyocr.Reader(self.languages, gpu=False)

        print("[OCR] Ready.")

    ##################################################

    @staticmethod
    def preprocess(frame):
        """
        Grayscale + contrast boost. Printed signage under
        overhead lighting reads noticeably better this way.
        """

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(
            clipLimit=2.0, tileGridSize=(8, 8)
        )

        return clahe.apply(gray)

    ##################################################

    def read(self, frame, preprocess=True):
        """
        Returns [{"text", "confidence", "box"}].
        """

        if frame is None:
            return []

        image = self.preprocess(frame) if preprocess else frame

        results = self.reader.readtext(image)

        out = []

        for box, text, confidence in results:

            if confidence < MIN_CONFIDENCE:
                continue

            xs = [int(p[0]) for p in box]
            ys = [int(p[1]) for p in box]

            out.append(
                {
                    "text": text.strip(),
                    "confidence": round(float(confidence), 2),
                    "box": (min(xs), min(ys), max(xs), max(ys)),
                }
            )

        return out

    ##################################################

    def read_text(self, frame):
        """Plain concatenated string, or None."""

        results = self.read(frame)

        if not results:
            return None

        return "\n".join(r["text"] for r in results)

    ##################################################

    def draw(self, frame, results):

        for item in results:

            x1, y1, x2, y2 = item["box"]

            cv2.rectangle(
                frame, (x1, y1), (x2, y2), (255, 0, 255), 2
            )

            cv2.putText(
                frame,
                item["text"],
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 255),
                2
            )

        return frame


####################################################
# Lazy singleton
####################################################

_ocr = None


def get_ocr(languages=None):

    global _ocr

    if _ocr is None:
        _ocr = OCR(languages)

    return _ocr


def read_text(frame):

    return get_ocr().read_text(frame)


def read_detailed(frame):

    return get_ocr().read(frame)


####################################################

if __name__ == "__main__":

    from vision.camera import get_camera, release_camera

    cam = get_camera()

    frame = cam.wait_for_frame()

    if frame is None:
        print("No frame.")
    else:
        print("Reading (this takes a few seconds)...\n")

        for item in get_ocr().read(frame):
            print(f"  [{item['confidence']:.2f}] {item['text']}")

    release_camera()