"""
map_storage.py

Save and Load Maps for Project Ved.

Maps are stored as JSON files.

Author: NeuraOS
"""

import json
import os


class MapStorage:

    def __init__(self):

        self.directory = "maps"

        os.makedirs(self.directory, exist_ok=True)

    # -----------------------------------------
    # Save Map
    # -----------------------------------------

    def save(self, name, map_data):

        filename = os.path.join(

            self.directory,

            f"{name}.json"

        )

        with open(filename, "w") as file:

            json.dump(

                map_data,

                file,

                indent=4

            )

        print(f"Map saved to {filename}")

    # -----------------------------------------
    # Load Map
    # -----------------------------------------

    def load(self, name):

        filename = os.path.join(

            self.directory,

            f"{name}.json"

        )

        if not os.path.exists(filename):

            print("Map not found.")

            return None

        with open(filename, "r") as file:

            return json.load(file)

    # -----------------------------------------
    # List Maps
    # -----------------------------------------

    def list_maps(self):

        return [

            file[:-5]

            for file in os.listdir(self.directory)

            if file.endswith(".json")

        ]

    # -----------------------------------------
    # Delete Map
    # -----------------------------------------

    def delete(self, name):

        filename = os.path.join(

            self.directory,

            f"{name}.json"

        )

        if os.path.exists(filename):

            os.remove(filename)

            print(f"{name} deleted.")

    # -----------------------------------------
    # Exists
    # -----------------------------------------

    def exists(self, name):

        filename = os.path.join(

            self.directory,

            f"{name}.json"

        )

        return os.path.exists(filename)


mapStorage = MapStorage()