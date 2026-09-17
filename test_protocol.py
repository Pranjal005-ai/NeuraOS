"""
ESP32 Protocol Test

Author: Pranjal
"""

from motion.esp32_protocol import protocol


print(protocol.FORWARD)

print(protocol.LEFT)

print(protocol.RIGHT)

print(protocol.STOP)

print(protocol.speed(150))

print(protocol.servo(90))

print(protocol.led(0,255,0))

print(protocol.buzzer(True))

print(protocol.buzzer(False))

print(protocol.HEARTBEAT)