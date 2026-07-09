import cv2
import numpy as np
from insightface.app import FaceAnalysis

from vision.face_database import load_faces


class FaceEngine:

    def __init__(self):

        self.app = FaceAnalysis(name="buffalo_l")

        self.app.prepare(
            ctx_id=0,
            det_size=(640, 640)
        )

        self.known_faces = load_faces()

    def get_face(self, image):

        faces = self.app.get(image)

        if len(faces) == 0:
            return None

        return faces[0]

    def register(self, image):

        face = self.get_face(image)

        if face is None:
            return None

        return face.embedding

    def recognize(self, image):

        face = self.get_face(image)

        if face is None:
            return None, 0

        embedding = face.embedding

        best_name = "Unknown"
        best_score = -1

        for name, saved_embedding in self.known_faces.items():

            score = np.dot(
                embedding,
                saved_embedding
            ) / (
                np.linalg.norm(embedding)
                * np.linalg.norm(saved_embedding)
            )

            if score > best_score:
                best_score = score
                best_name = name

        if best_score < 0.45:
            best_name = "Unknown"

        return best_name, best_score