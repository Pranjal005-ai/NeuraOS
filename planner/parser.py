"""
parser.py

Converts AI decisions into robot missions.
"""

from planner.action import Action
from planner.mission import Mission


def create_food_delivery(items, destination):

    mission = Mission("Food Delivery")

    for item in items:

        mission.add_action(
            Action(
                "NAVIGATE",
                target=f"{item} Counter"
            )
        )

        mission.add_action(
            Action(
                "WAIT"
            )
        )

    mission.add_action(

        Action(
            "NAVIGATE",
            target=destination
        )

    )

    mission.add_action(

        Action(
            "SPEAK",
            data="Your order has arrived."
        )

    )

    return mission