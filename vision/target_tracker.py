"""
target_tracker.py

Keeps track of which person Ved should follow.
"""

_target_name = None


def set_target(name):

    global _target_name

    _target_name = name


def get_target():

    return _target_name


def clear_target():

    global _target_name

    _target_name = None


def has_target():

    return _target_name is not None