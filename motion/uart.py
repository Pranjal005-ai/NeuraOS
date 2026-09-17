"""
==================================================
Project Ved (NeuraOS)

Module: uart.py

Description:
UART communication between Raspberry Pi 5 and ESP32.

Author: Pranjal
==================================================
"""

import serial
import time


class UART:

    def __init__(
        self,
        port="/dev/serial0",
        baudrate=115200
    ):

        self.port = port
        self.baudrate = baudrate
        self.serial = None

    # -----------------------------------------
    # Connect
    # -----------------------------------------

    def connect(self):

        try:

            self.serial = serial.Serial(

                self.port,
                self.baudrate,
                timeout=1

            )

            time.sleep(2)

            print("UART Connected")

        except Exception as e:

            print("UART Error:", e)

            self.serial = None

    # -----------------------------------------
    # Connected?
    # -----------------------------------------

    def connected(self):

        return self.serial is not None

    # -----------------------------------------
    # Send
    # -----------------------------------------

    def send(self, message):

        if not self.connected():

            return False

        self.serial.write(

            (message + "\n").encode()

        )

        return True

    # -----------------------------------------
    # Receive
    # -----------------------------------------

    def receive(self):

        if not self.connected():

            return None

        if self.serial.in_waiting:

            return self.serial.readline().decode().strip()

        return None

    # -----------------------------------------
    # Close
    # -----------------------------------------

    def close(self):

        if self.connected():

            self.serial.close()

            self.serial = None


uart = UART()