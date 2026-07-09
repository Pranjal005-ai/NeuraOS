import cv2

cap = cv2.VideoCapture(0)

print("Opened:", cap.isOpened())

ret, frame = cap.read()

print("ret =", ret)

if ret:
    cv2.imwrite("test.jpg", frame)
    print("✅ Image saved as test.jpg")
else:
    print("❌ Could not read frame")

cap.release()