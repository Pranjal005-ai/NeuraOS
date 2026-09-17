import cv2

from vision.object_detector import detect_objects
from vision.object_summary import summarize_objects

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not found")
    exit()

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    detections = detect_objects(frame)

    summary = summarize_objects(detections)

    cv2.putText(
        frame,
        summary,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0,255,0),
        2
    )

    cv2.imshow("Ved Object Summary", frame)

    print(summary)

    if cv2.waitKey(1) == 27:
        break

cap.release()

cv2.destroyAllWindows()