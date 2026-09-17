"""
hotel_mode.py

Main Hotel Mode Controller.
"""

from core.state import state_manager, RobotState


class HotelMode:

    def __init__(self):

        self.enabled = False

    def start(self):

        self.enabled = True

        state_manager.set(RobotState.HOTEL_MODE)

        print("[HOTEL] Hotel Mode Enabled")

    def stop(self):

        self.enabled = False

        state_manager.set(RobotState.IDLE)

        print("[HOTEL] Hotel Mode Disabled")


hotel_mode = HotelMode()