"""
test_motors.py

Simple test for Ved's movement.
"""

import time

from motion.motor_controller import (
    forward,
    backward,
    left,
    right,
    stop,
    cleanup
)

try:

    print("Forward")
    forward()
    time.sleep(2)

    print("Stop")
    stop()
    time.sleep(1)

    print("Backward")
    backward()
    time.sleep(2)

    print("Stop")
    stop()
    time.sleep(1)

    print("Left")
    left()
    time.sleep(2)

    print("Stop")
    stop()
    time.sleep(1)

    print("Right")
    right()
    time.sleep(2)

    print("Stop")
    stop()

finally:

    cleanup()