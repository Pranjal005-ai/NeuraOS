"""
Follow Skill
"""

from vision.person_tracker import tracker


def start_following():

    tracker.start()

    return "I'll follow you."


def stop_following():

    tracker.stopFollowing()

    return "Stopped following."