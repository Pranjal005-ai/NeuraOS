import cv2

for i in range(6):
    cap = cv2.VideoCapture(i)

    if cap.isOpened():
        ret, frame = cap.read()

        print(f"Camera {i}: Opened={cap.isOpened()}  Frame={ret}")

        if ret:
            cv2.imwrite(f"camera_{i}.jpg", frame)

    cap.release()