from vision.camera import capture
from ai.vision_ai import describe_image

print("📷 Capturing image...")

image = capture()

print("🧠 Thinking...")

answer = describe_image(image)

print(answer)