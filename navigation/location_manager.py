"""
location_manager.py

Stores known locations for Project Ved.

Initially this is a simple in-memory database.

Later this will be replaced by:
- SLAM map
- Hotel map
- Hospital map
- Dynamic locations

Author: NeuraOS
"""


class LocationManager:

    def __init__(self):

        # --------------------------------------------------
        # Known Locations
        # --------------------------------------------------

        self.locations = {

            "home": (0, 0),

            "charging station": (0, 0),

            "reception": (5, 2),

            "lobby": (10, 4),

            "kitchen": (15, 7),

            "room 101": (20, 10),

            "room 102": (25, 10),

            "room 201": (30, 18),

            "room 202": (35, 18),

            "room 205": (42, 20)

        }

    # --------------------------------------------------
    # Check if location exists
    # --------------------------------------------------

    def exists(self, location):

        return location.lower() in self.locations

    # --------------------------------------------------
    # Get coordinates
    # --------------------------------------------------

    def get(self, location):

        return self.locations.get(location.lower())

    # --------------------------------------------------
    # Add new location
    # --------------------------------------------------

    def add(self, name, coordinates):

        self.locations[name.lower()] = coordinates

    # --------------------------------------------------
    # Remove location
    # --------------------------------------------------

    def remove(self, name):

        self.locations.pop(name.lower(), None)

    # --------------------------------------------------
    # List all locations
    # --------------------------------------------------

    def all(self):

        return self.locations


# Singleton

locationManager = LocationManager()