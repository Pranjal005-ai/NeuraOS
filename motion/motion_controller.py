"""
==================================================
Project Ved (NeuraOS)

Module: motion_controller.py

Description:
Controls Ved's movement by sending commands
to the ESP32.

Author: Pranjal
==================================================
"""

from motion.uart import uart
from motion.esp32_protocol import protocol


class MotionController:

    def __init__(self):

        self.speed = 150

    # -----------------------------------------
    # Connect
    # -----------------------------------------

    def connect(self):

        uart.connect()

    # -----------------------------------------
    # Set Speed
    # -----------------------------------------

    def set_speed(self, speed):

        self.speed = speed

        uart.send(

            protocol.speed(speed)

        )

    # -----------------------------------------
    # Move Forward
    # -----------------------------------------

    def forward(self):

        uart.send(

            protocol.FORWARD

        )

    # -----------------------------------------
    # Move Backward
    # -----------------------------------------

    def backward(self):

        uart.send(

            protocol.BACKWARD

        )

    # -----------------------------------------
    # Turn Left
    # -----------------------------------------

    def left(self):

        uart.send(

            protocol.LEFT

        )

    # -----------------------------------------
    # Turn Right
    # -----------------------------------------

    def right(self):

        uart.send(

            protocol.RIGHT

        )

    # -----------------------------------------
    # Stop
    # -----------------------------------------

    def stop(self):

        uart.send(

            protocol.STOP

        )

    # -----------------------------------------
    # Servo
    # -----------------------------------------

    def servo(self, angle):

        uart.send(

            protocol.servo(angle)

        )

    # -----------------------------------------
    # LED
    # -----------------------------------------

    def led(self, r, g, b):

        uart.send(

            protocol.led(r, g, b)

        )

    # -----------------------------------------
    # Buzzer
    # -----------------------------------------

    def buzzer(self, state):

        uart.send(

            protocol.buzzer(state)

        )

    # -----------------------------------------
    # Disconnect
    # -----------------------------------------

    def disconnect(self):

        uart.close()


motionController = MotionController()