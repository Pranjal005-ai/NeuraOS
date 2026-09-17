"""
scheduler.py

Task Scheduler for Ved.

Maintains a queue of missions and executes
them one by one.
"""

from planner.mission_executor import executor


class Scheduler:

    def __init__(self):

        self.queue = []

        self.current = None

    # ------------------------------------------

    def addMission(self, mission):

        print(f"[SCHEDULER] Added: {mission.name}")

        self.queue.append(mission)

    # ------------------------------------------

    def update(self):

        # Already executing something

        if self.current:

            return

        # Nothing in queue

        if not self.queue:

            return

        # Get next mission

        self.current = self.queue.pop(0)

        executor.execute(self.current)

        self.current = None


scheduler = Scheduler()