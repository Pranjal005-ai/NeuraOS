"""
task_manager.py

Handles queued robot tasks.
"""

class TaskManager:

    def __init__(self):

        self.tasks = []

    def add(self, task):

        print(f"Task Added: {task}")

        self.tasks.append(task)

    def next(self):

        if not self.tasks:

            return None

        return self.tasks.pop(0)


task_manager = TaskManager()