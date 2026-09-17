"""
==================================================
Project Ved

Motion Controller Test

Author: Pranjal
==================================================
"""

import time

from motion.motion_controller import motionController


motionController.connect()

motionController.set_speed(180)

time.sleep(1)

print("Forward")

motionController.forward()

time.sleep(2)

print("Left")

motionController.left()

time.sleep(2)

print("Forward")

motionController.forward()

time.sleep(2)

print("Right")

motionController.right()

time.sleep(2)

print("Backward")

motionController.backward()

time.sleep(2)

print("Stop")

motionController.stop()

motionController.disconnect()