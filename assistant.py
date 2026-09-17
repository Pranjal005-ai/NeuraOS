"""
=========================================================
assistant.py

Central Controller for Project Ved / NeuraOS

Author: Pranjal

THREE BUGS FIXED IN THE MEMORY MIGRATION
----------------------------------------
1. `person` was undefined. learn_from(person, command)
   raised NameError on every command. The identity now
   comes from the session, falling back to "Unknown".

2. `memory_data` was undefined. The old parse_memory()
   assignment was removed but the `if memory_data:` block
   below it was left behind, referencing a name that no
   longer existed.

3. THE SUBTLE ONE: command.lower().strip() at the top
   destroyed casing before personal_memory ever saw it,
   so names were stored as "pranjal" and Ved replied
   "Your name is pranjal." The whole point of the
   rewrite was preserving the original text.

   Now: `command` keeps its original casing, and a
   separate lowered copy is used for the keyword
   matching that genuinely needs it.
=========================================================
"""

import re

from ai.brain import Brain
from ai.chatgpt import ask_ai

from memory.personal_memory import personal_memory

from skills.greetings import greet
from skills.about import about
from skills.time_skill import current_time
from skills.vision import see
from planner.parser import create_food_delivery
from core.robot_manager import robotManager
from skills.object_search import search_object
from skills.qr_scan import scan_qr
from skills.ocr import read_text

from skills.follow import (
    start_following,
    stop_following
)

from motion.motor_controller import (
    forward,
    backward,
    left,
    right,
    stop
)


brain = Brain()


class Assistant:

    ####################################################

    @staticmethod
    def who_is_speaking(session):
        """
        Which person is Ved talking to?

        Memory is stored per person, so this decides whose
        memory gets written. Falls back to "Unknown", which
        still works -- facts just aren't separated by
        speaker until face recognition supplies a name.
        """

        if session is None:
            return "Unknown"

        partner = getattr(session, "partner", None)

        return partner or "Unknown"

    ####################################################

    def handle(self, command, session=None):

        # Keep the ORIGINAL text. Lowercasing here was
        # what corrupted stored names.
        command = (command or "").strip()

        # A lowered copy, purely for keyword matching.
        lowered = command.lower()

        person = self.who_is_speaking(session)

        print("\n==============================")
        print("USER :", command)
        print("==============================")

        # =====================================
        # GREETING
        # =====================================

        if re.fullmatch(r"(hi|hello|namaste)", lowered):

            print("Greeting Skill")

            return greet()

        # =====================================
        # ABOUT
        # =====================================

        elif (
            "who are you" in lowered
            or "introduce yourself" in lowered
        ):

            print("About Skill")

            return about()

        # =====================================
        # TIME
        # =====================================

        elif "time" in lowered:

            print("Time Skill")

            return current_time()

        # =====================================
        # VISION
        # =====================================

        elif (
            "what do you see" in lowered
            or "what can you see" in lowered
            or "look around" in lowered
            or "describe this" in lowered
            or "describe the room" in lowered
            or "who is in front of you" in lowered
        ):

            print("Vision Skill")

            return see()

        # =====================================
        # DECISION ENGINE
        # =====================================

        decision = brain.process_command(command)

        print("Decision :", decision)

        # =====================================
        # MEMORY -- LEARN
        #
        # Runs on the ORIGINAL command so casing survives.
        # Returns the keys learned, so Ved can confirm
        # what it picked up.
        # =====================================

        learned = personal_memory.learn_from(person, command)

        if learned:

            print(f"Memory saved for {person}: {learned}")

            facts = ", ".join(
                f"your {key.replace('_', ' ')} is "
                f"{personal_memory.recall(person, key)}"
                for key in learned
            )

            return f"I'll remember that — {facts}."

        # =====================================
        # MEMORY -- RECALL
        #
        # answer() returns (reply, known). reply is None
        # when this isn't a memory question at all, which
        # is different from "asked but I don't know" --
        # so we fall through only in the first case.
        # =====================================

        memory_answer, known = personal_memory.answer(person, command)

        if memory_answer is not None:

            print(f"Memory recall for {person} (known={known})")

            return memory_answer

        # =====================================
        # MOVEMENT
        # =====================================

        if decision == "MOVE_FORWARD":

            print("Move Forward")

            forward()

            return "Moving forward."

        elif decision == "MOVE_BACKWARD":

            print("Move Backward")

            backward()

            return "Moving backward."

        elif decision == "TURN_LEFT":

            print("Turn Left")

            left()

            return "Turning left."

        elif decision == "TURN_RIGHT":

            print("Turn Right")

            right()

            return "Turning right."

        elif decision == "STOP":

            print("Stop")

            stop()

            return "Stopping."

        # =====================================
        # CHATGPT
        # =====================================

        elif decision == "CHAT":

            print("ChatGPT")

            return ask_ai(command, session)

        # =====================================
        # OBJECT SEARCH
        # =====================================

        elif decision == "OBJECT_SEARCH":

            object_name = re.sub(
                r"\b(find|search for|look for)\b",
                "",
                command,
                flags=re.IGNORECASE
            ).strip()

            if not object_name:
                return "What would you like me to find?"

            return search_object(object_name)

        # =====================================
        # FOLLOWING
        # =====================================

        elif decision == "FOLLOW":

            return start_following()

        elif decision == "STOP_FOLLOW":

            return stop_following()

        # =====================================
        # QR SCANNER
        # =====================================

        elif decision == "QR_SCAN":

            print("Scanning QR code...")

            return scan_qr()

        # =====================================
        # OCR
        # =====================================

        elif decision == "OCR":

            print("Reading text...")

            return read_text()

        # =====================================
        # UNKNOWN
        # =====================================

        print("Unknown command")

        return "Sorry, I didn't understand."