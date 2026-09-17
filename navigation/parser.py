"""
parser.py

Navigation Command Parser

Extracts destination names from natural language commands.

Examples:
    "Go to room 205"
        -> room 205

    "Take me to reception"
        -> reception

    "Navigate to kitchen"
        -> kitchen
"""

from navigation.location_manager import locationManager


class NavigationParser:

    def extractDestination(self, command):

        command = command.lower()

        # ---------------------------------------
        # Search every known location
        # ---------------------------------------

        for location in locationManager.all():

            if location in command:

                return location

        return None


# Singleton

navigationParser = NavigationParser()