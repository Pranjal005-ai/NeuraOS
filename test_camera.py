from vision.camera import capture

print("📸 Testing Camera...")

image = capture()

if image:
    print("✅ Image captured:", image)
else:
    print("❌ Camera failed")