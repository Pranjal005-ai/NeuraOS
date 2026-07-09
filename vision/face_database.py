import os
import numpy as np

DATABASE = "vision/known_faces"


def save_face(name, embedding):

    folder = os.path.join(DATABASE, name)

    os.makedirs(folder, exist_ok=True)

    np.save(
        os.path.join(folder, "embedding.npy"),
        embedding
    )


def load_faces():

    faces = {}

    if not os.path.exists(DATABASE):
        return faces

    for person in os.listdir(DATABASE):

        path = os.path.join(
            DATABASE,
            person,
            "embedding.npy"
        )

        if os.path.exists(path):

            faces[person] = np.load(path)

    return faces