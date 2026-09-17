"""
room_service.py

Handles room service requests.
"""

from core.task_manager import task_manager


def createRoomService(room, items):

    task = {

        "type": "ROOM_SERVICE",

        "room": room,

        "items": items

    }

    task_manager.add(task)

    print("[ROOM SERVICE]", task)