"""
High level robot movement commands.
"""

from .esp32 import esp32


def forward():
    esp32.send("FORWARD")


def backward():
    esp32.send("BACKWARD")


def left():
    esp32.send("LEFT")


def right():
    esp32.send("RIGHT")


def stop():
    esp32.send("STOP")