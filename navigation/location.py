"""
location.py

Stores all known robot locations.
"""


class Location:

    def __init__(self, name):

        self.name = name


LOCATIONS = {

    "Reception": Location("Reception"),

    "Kitchen": Location("Kitchen"),

    "Tea Counter": Location("Tea Counter"),

    "Dosa Counter": Location("Dosa Counter"),

    "Room 101": Location("Room 101"),

    "Charging Dock": Location("Charging Dock")
}