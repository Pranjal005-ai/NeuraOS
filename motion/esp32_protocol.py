"""
==================================================
Project Ved (NeuraOS)

Module: esp32_protocol.py

Description:
Protocol used for communication between
Raspberry Pi and ESP32.

Author: Pranjal
==================================================
"""


class ESP32Protocol:

    # ------------------------------
    # Motion Commands
    # ------------------------------

    FORWARD = "FORWARD"

    BACKWARD = "BACKWARD"

    LEFT = "LEFT"

    RIGHT = "RIGHT"

    STOP = "STOP"

    # ------------------------------
    # Speed
    # ------------------------------

    @staticmethod
    def speed(value):

        return f"SPEED:{value}"

    # ------------------------------
    # Servo
    # ------------------------------

    @staticmethod
    def servo(angle):

        return f"SERVO:{angle}"

    # ------------------------------
    # RGB LED
    # ------------------------------

    @staticmethod
    def led(r, g, b):

        return f"LED:{r},{g},{b}"

    # ------------------------------
    # Buzzer
    # ------------------------------

    @staticmethod
    def buzzer(state):

        if state:

            return "BUZZER:ON"

        return "BUZZER:OFF"

    # ------------------------------
    # Heartbeat
    # ------------------------------

    HEARTBEAT = "PING"

    ACK = "ACK"


protocol = ESP32Protocol()