"""
=========================================================
object_detector.py

Real-time object detection using YOLOv8n.

Run from the PROJECT ROOT:
    python3 -m vision.object_detector

Author: Pranjal

CHANGES FROM THE PREVIOUS VERSION
---------------------------------
1. LAZY. `detector = ObjectDetector()` at module scope
   loaded YOLO on import, so anything importing this
   file paid ~1s and a few hundred MB whether or not it
   ever detected anything.
2. The debug print fired BEFORE the ALLOWED_OBJECTS
   filter, flooding stdout every frame with objects Ved
   ignores. Now off by default.
3. Live preview uses the shared camera wrapper, so it
   works on the Pi's CSI camera.
=========================================================
"""

import cv2

from vision.config import YOLO_MODEL_PATH


CONFIDENCE_THRESHOLD = 0.25

VERBOSE = False


# Objects Ved actually cares about
ALLOWED_OBJECTS = {
    "person",
    "chair", "couch", "bed",
    "bottle", "cup",
    "laptop", "keyboard", "mouse", "cell phone", "tv",
    "book",
    "backpack", "handbag", "suitcase",
    "dining table",
    "refrigerator", "microwave", "oven", "sink",
    "clock",
    "potted plant",
}


class ObjectDetector:

    def __init__(self):

        from ultralytics import YOLO

        print("[YOLO] Loading YOLOv8n...")

        if not YOLO_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found: {YOLO_MODEL_PATH}"
            )

        self.model = YOLO(str(YOLO_MODEL_PATH))

        print("[YOLO] Ready.")

    ##################################################

    def detect(self, frame):
        """
        Returns [{"label", "confidence", "box"}].
        """

        if frame is None:
            return []

        results = self.model(frame, verbose=False)[0]

        detections = []

        for box in results.boxes:

            confidence = float(box.conf[0])

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            label = self.model.names[int(box.cls[0])]

            # Filter BEFORE logging.
            if label not in ALLOWED_OBJECTS:
                continue

            if VERBOSE:
                print(f"{label} : {confidence:.2f}")

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            detections.append(
                {
                    "label": label,
                    "confidence": round(confidence, 2),
                    "box": (x1, y1, x2, y2),
                }
            )

        return detections

    ##################################################

    def summarize(self, detections):

        if not detections:
            return "I don't see anything I recognize."

        counts = {}

        for obj in detections:
            counts[obj["label"]] = counts.get(obj["label"], 0) + 1

        parts = []

        for label in sorted(counts):

            count = counts[label]

            parts.append(
                f"one {label}" if count == 1
                else f"{count} {label}s"
            )

        return "I can see " + ", ".join(parts) + "."

    ##################################################

    def draw(self, frame, detections):

        for obj in detections:

            x1, y1, x2, y2 = obj["box"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.putText(
                frame,
                f"{obj['label']} {obj['confidence']:.2f}",
                (x1, max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        return frame


####################################################
# Lazy singleton
####################################################

_detector = None


def get_detector():

    global _detector

    if _detector is None:
        _detector = ObjectDetector()

    return _detector


def detect_objects(frame):

    return get_detector().detect(frame)


def describe_detections(detections):

    return get_detector().summarize(detections)


def draw_detections(frame, detections):

    return get_detector().draw(frame, detections)


####################################################
# Live test
####################################################

def run_live_preview():

    from vision.camera import get_camera, release_camera

    detector = get_detector()

    cam = get_camera()

    if cam.wait_for_frame() is None:
        print("No frames from camera.")
        return

    print("=" * 52)
    print("VED OBJECT DETECTION -- press Q to quit")
    print("=" * 52)

    try:
        while True:

            frame = cam.get_frame()

            if frame is None:
                continue

            detections = detector.detect(frame)

            detector.draw(frame, detections)

            cv2.putText(
                frame,
                detector.summarize(detections),
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )

            cv2.imshow("Ved Object Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cv2.destroyAllWindows()
        release_camera()


if __name__ == "__main__":
    run_live_preview()