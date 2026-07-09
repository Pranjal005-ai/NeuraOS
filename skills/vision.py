from vision.camera import capture
from ai.vision_ai import describe_image

def see():

    print("📸 Vision started")

    image = capture()

    print("Captured:", image)

    if image is None:
        return "I couldn't capture an image."

    print("Sending to GPT Vision...")

    answer = describe_image(image)

    print("GPT replied.")

    return answer