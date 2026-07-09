from vision.face_engine import FaceEngine

engine = FaceEngine()


def get_target(frame):

    name, score = engine.recognize(frame)

    if score > 0.60:
        return name

    return None