"""
restaurant.py

Restaurant pickup logic.
"""

RESTAURANT_COUNTERS = {

    "Tea": "Tea Counter",

    "Coffee": "Coffee Counter",

    "Dosa": "Dosa Counter",

    "Pizza": "Pizza Counter",

    "Burger": "Burger Counter"

}


def getCounter(item):

    return RESTAURANT_COUNTERS.get(item)