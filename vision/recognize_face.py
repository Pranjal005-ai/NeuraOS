import cv2

from vision.face_engine import FaceEngine
from vision.target_tracker import lock_target

engine = FaceEngine()

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not found.")
    exit()

print("Recognition started...")
print("Press ESC to quit.")

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    result = engine.recognize(frame)

    if name != "Unknown":
      lock_target(name)

    if result is None:
        continue

    name, score = result

    cv2.putText(
        frame,
        f"{name} ({score:.2f})",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )

    cv2.imshow("Ved Face Recognition", frame)

    key = cv2.waitKey(1)

    if key == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()