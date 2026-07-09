import cv2
from ultralytics import YOLO

from vision.follow_logic import follow_person
from vision.target_tracker import get_target
from vision.face_tracker import get_target

# -----------------------------
# Load YOLO
# -----------------------------
model = YOLO("yolov8n.pt")

# -----------------------------
# Open Camera
# -----------------------------
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera not found")
    exit()

print("=" * 50)
print("VED PERSON FOLLOWING STARTED")
print("Press ESC to quit")
print("=" * 50)

last_command = ""

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    frame_width = frame.shape[1]
    frame_height = frame.shape[0]

    # -----------------------------
    # Draw Center Line
    # -----------------------------
    cv2.line(
        frame,
        (frame_width // 2, 0),
        (frame_width // 2, frame_height),
        (255, 0, 0),
        2
    )

    # -----------------------------
    # Draw Dead Zone
    # -----------------------------
    left_zone = int(frame_width * 0.45)
    right_zone = int(frame_width * 0.55)

    cv2.line(
        frame,
        (left_zone, 0),
        (left_zone, frame_height),
        (0, 255, 255),
        2
    )

    cv2.line(
        frame,
        (right_zone, 0),
        (right_zone, frame_height),
        (0, 255, 255),
        2
    )

    # -----------------------------
    # Run YOLO
    # -----------------------------
    results = model(frame, verbose=False)

    best_box = None
    best_area = 0
    best_confidence = 0

    # -----------------------------
    # Select Largest Person
    # -----------------------------
    for box in results[0].boxes:

        cls = int(box.cls[0])

        if cls != 0:
            continue

        confidence = float(box.conf[0])

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        area = (x2 - x1) * (y2 - y1)

        if area > best_area:
            best_area = area
            best_box = (x1, y1, x2, y2)
            best_confidence = confidence

    # -----------------------------
    # Person Found
    # -----------------------------
    if best_box is not None and target is not None:

        x1, y1, x2, y2 = best_box

        movement = follow_person(best_box, frame_width)

        # Show target if locked
        target = get_target(frame)

        if target:
            cv2.putText(
                frame,
                f"Following: {target}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2
            )

        # Print only if movement changed
        if movement != last_command:
            print("➡", movement)
            last_command = movement

        # Draw bounding box
        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        # Draw movement
        cv2.putText(
            frame,
            movement,
            (x1, y1 - 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        # Draw confidence
        cv2.putText(
            frame,
            f"Confidence: {best_confidence:.2f}",
            (x1, y1 - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2
        )

    # -----------------------------
    # Display
    # -----------------------------
    cv2.imshow("Ved Person Following", frame)

    key = cv2.waitKey(1)

    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()