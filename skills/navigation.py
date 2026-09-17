"""
navigation.py

Navigation Skill

Responsibilities:
- Understand navigation commands
- Extract destination
- Start navigation

Author: NeuraOS
"""

from navigation.parser import navigationParser
from navigation.navigator import navigator


def navigate(command):
    """
    Process a navigation command.

    Example:
        Go to room 205
        Take me to reception
    """

    # ------------------------------------------
    # Find destination
    # ------------------------------------------

    destination = navigationParser.extractDestination(command)

    if destination is None:

        return "I couldn't find that location."

    # ------------------------------------------
    # Start navigation
    # ------------------------------------------

    return navigator.goTo(destination)


def stop_navigation():
    """
    Stop current navigation.
    """

    return navigator.stop()