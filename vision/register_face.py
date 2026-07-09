import os
import cv2

from vision.face_engine import FaceEngine
from vision.face_database import save_face

engine = FaceEngine()

name = input("Enter person's name: ").strip()

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not found.")
    exit()

print("\nLook at the camera.")
print("Press SPACE once to register.")
print("Press ESC to cancel.")

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    cv2.imshow("Register Face", frame)

    key = cv2.waitKey(1)

    if key == 32:  # SPACE

        embedding = engine.register(frame)

        if embedding is None:
            print("No face detected. Try again.")
            continue

        folder = f"vision/known_faces/{name}"
        os.makedirs(folder, exist_ok=True)

        image_path = os.path.join(folder, "profile.jpg")

        cv2.imwrite(image_path, frame)

        save_face(name, embedding)

        print(f"\n✅ Registered {name}")

        break

    elif key == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()