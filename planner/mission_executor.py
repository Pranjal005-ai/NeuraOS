"""
mission_executor.py

Executes robot missions.
"""

from navigation.navigator import navigator


class MissionExecutor:

    def execute(self, mission):

        print(f"Executing Mission: {mission.name}")

        for action in mission.actions:

            print(action)

            if action.action_type == "NAVIGATE":

                navigator.go_to(action.target)

            elif action.action_type == "WAIT":

                print("Waiting...")

            elif action.action_type == "SPEAK":

                print(action.data)


executor = MissionExecutor()