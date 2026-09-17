"""
UART Test

Author: Pranjal
"""

from motion.uart import uart

uart.connect()

if uart.connected():

    print("Sending...")

    uart.send("HELLO")

    while True:

        message = uart.receive()

        if message:

            print("ESP32:", message)

            break

uart.close()