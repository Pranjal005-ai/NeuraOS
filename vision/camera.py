import cv2

def capture():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Camera not opened")
        return None

    print("📷 Press SPACE to capture")

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        cv2.imshow("Camera", frame)

        key = cv2.waitKey(1)

        # SPACE = Capture
        if key == 32:

            filename = "capture.jpg"

            cv2.imwrite(filename, frame)

            print("✅ Image saved")

            break

        # ESC = Cancel
        elif key == 27:

            filename = None

            break

    cap.release()
    cv2.destroyAllWindows()

    return filename