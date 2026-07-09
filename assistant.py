"""
assistant.py
Central Controller for Project Ved / NeuraOS
"""

import re

from ai.brain import Brain
from ai.chatgpt import ask_ai

from memory.memory import Memory
from ai.memory_parser import parse_memory
from ai.memory_search import search_memory

from skills.greetings import greet
from skills.about import about
from skills.time_skill import current_time
from skills.vision import see


brain = Brain()
memory = Memory()


class Assistant:

    def handle(self, command, session):

        command = command.lower().strip()

        print("\n==============================")
        print("📥 USER :", command)
        print("==============================")

        # =====================================
        # GREETING
        # =====================================

        if re.fullmatch(r"(hi|hello|namaste)", command):

            print("🟢 Greeting Skill")

            return greet()

        # =====================================
        # ABOUT
        # =====================================

        elif (
            "who are you" in command
            or "introduce yourself" in command
        ):

            print("🟢 About Skill")

            return about()

        # =====================================
        # TIME
        # =====================================

        elif (
            "time" in command
            or "what time" in command
        ):

            print("🟢 Time Skill")

            return current_time()

        # =====================================
        # DECISION ENGINE
        # =====================================

        decision = brain.process_command(command)

        print("🧠 Decision :", decision)

        # =====================================
        # SMART MEMORY SAVE
        # =====================================

        memory_data = parse_memory(command)

        if memory_data:

            key, value = memory_data

            memory.remember(key, value)

            print("🟢 Memory Saved")

            return (
                f"I'll remember that. "
                f"Your {key.replace('_',' ')} is {value}."
            )

        # =====================================
        # MEMORY SEARCH
        # =====================================

        memory_answer = search_memory(command)

        if memory_answer:

            print("🟢 Memory Search")

            return memory_answer

        # =====================================
        # VISION
        # =====================================

        if (

            "what do you see" in command
            or "what can you see" in command
            or "look around" in command
            or "describe this" in command
            or "describe the room" in command
            or "who is in front of you" in command

        ):

            print("🟢 Vision Skill")

            return see()

        # =====================================
        # MOVEMENT
        # =====================================

        if decision == "MOVE_FORWARD":

            print("🟢 Move Forward")

            return "Moving Forward."

        elif decision == "MOVE_BACKWARD":

            print("🟢 Move Backward")

            return "Moving Backward."

        elif decision == "TURN_LEFT":

            print("🟢 Turn Left")

            return "Turning Left."

        elif decision == "TURN_RIGHT":

            print("🟢 Turn Right")

            return "Turning Right."

        elif decision == "STOP":

            print("🟢 Stop")

            return "Stopping."

        # =====================================
        # CHATGPT
        # =====================================

        elif decision == "CHAT":

            print("🟢 ChatGPT")

            return ask_ai(command, session)

        # =====================================
        # UNKNOWN
        # =====================================

        print("🔴 Unknown Command")

        return "Sorry, I didn't understand."