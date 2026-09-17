"""
delivery.py

Delivery workflow.
"""

from navigation.navigator import navigator
from navigation.location import LOCATIONS


def deliver(room):

    navigator.go_to(room)

    print(f"Delivering order to {room}")