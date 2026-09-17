"""
robot_manager.py

Central Robot Manager for Project Ved / NeuraOS

Responsibilities:
- Manage robot state
- Receive missions
- Execute queued missions
- Read ESP32 sensor data
- Monitor robot health
- Future:
    - Auto charging
    - Emergency handling
    - Navigation monitoring
"""

from core.state import (
    state_manager,
    RobotState
)

from planner.scheduler import scheduler
from esp32.sensors import getSensors


class RobotManager:

    def __init__(self):

        # Current mission being executed
        self.currentMission = None

        # Latest sensor values received
        self.sensorData = {}

        # Robot status
        self.ready = True

    # =====================================================
    # Assign Mission
    # =====================================================

    def assignMission(self, mission):

        print("=" * 50)
        print(f"📋 New Mission : {mission.name}")
        print("=" * 50)

        self.currentMission = mission

        scheduler.addMission(mission)

        state_manager.set(RobotState.THINKING)

    # =====================================================
    # Read ESP32 Sensors
    # =====================================================

    def updateSensors(self):

        data = getSensors()

        if data:

            self.sensorData = data

    # =====================================================
    # Return Latest Sensor Values
    # =====================================================

    def getSensors(self):

        return self.sensorData

    # =====================================================
    # Robot Health
    # =====================================================

    def isReady(self):

        return self.ready

    # =====================================================
    # Emergency Stop
    # =====================================================

    def emergencyStop(self):

        print("🚨 EMERGENCY STOP")

        state_manager.set(
            RobotState.EMERGENCY_STOP
        )

    # =====================================================
    # Main Update Loop
    # =====================================================

    def update(self):

        # ---------------------------------------
        # Read latest ESP32 data
        # ---------------------------------------

        print("A")


         #self.updateSensors() # <-- temporarily disable

        # ---------------------------------------
        # Execute pending missions
        # ---------------------------------------

        print("B")

        scheduler.update()

        print("C")

        # ---------------------------------------
        # Future:
        #
        # Battery Monitoring
        # Auto Docking
        # Navigation Monitoring
        # Person Tracking
        # Obstacle Avoidance
        # Fleet Sync
        # ---------------------------------------

        return


# ==========================================================
# Singleton
# ==========================================================

robotManager = RobotManager()