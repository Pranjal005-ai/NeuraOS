"""
navigator.py

Navigator for Project Ved / NeuraOS

Responsibilities:
- Navigate to known locations
- Stop navigation
- Return current destination

Future:
- Path Planning
- LiDAR
- SLAM
- Dynamic Obstacle Avoidance
"""

from navigation.location_manager import locationManager


class Navigator:

    def __init__(self):

        # Current destination
        self.destination = None

        # Navigation status
        self.isNavigating = False

    # --------------------------------------------------
    # Navigate to location
    # --------------------------------------------------

    def goTo(self, location):

        location = location.lower()

        if not locationManager.exists(location):

            return f"I don't know where '{location}' is."

        self.destination = location

        self.isNavigating = True

        coordinates = locationManager.get(location)

        print("=" * 50)
        print("Navigation Started")
        print(f"Destination : {location}")
        print(f"Coordinates : {coordinates}")
        print("=" * 50)

        # Future:
        # pathPlanner.plan()
        # robotManager.startMission()
        # esp32.drive()

        return f"Navigating to {location}."

    # --------------------------------------------------
    # Stop Navigation
    # --------------------------------------------------

    def stop(self):

        self.destination = None
        self.isNavigating = False

        print("Navigation Stopped")

        return "Navigation stopped."

    # --------------------------------------------------
    # Current Destination
    # --------------------------------------------------

    def currentDestination(self):

        return self.destination

    # --------------------------------------------------
    # Navigation Status
    # --------------------------------------------------

    def navigating(self):

        return self.isNavigating


# Singleton

navigator = Navigator()