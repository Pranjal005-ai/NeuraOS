"""
robot.py

Main entry point for Ved.

Responsibilities:
- Wake word detection
- Speech recognition
- Session management
- AI conversation
- Mission execution
"""

from voice.speech_listener import listen
from assistant import Assistant
from wakeword.detector import is_awake
from core.session import Session
from core.robot_manager import robotManager

assistant = Assistant()
session = Session()

print("=" * 50)
print("🤖 PROJECT VED STARTED")
print("=" * 50)

while True:

    # --------------------------------------------------
    # Allow robot to continue running current missions
    # --------------------------------------------------
    print("1")
    robotManager.update()
    print("2")

    print("\n🎤 Listening...")

    command = listen()

    print("3")

    if command == "":
        continue

    print("You:", command)

    # --------------------------------------------------
    # Robot Sleeping
    # --------------------------------------------------

    if not session.is_active():

        if is_awake(command):

            session.wake()

            print("🤖 Ved: Yes? How can I help you?")

        else:

            print("😴 Sleeping...")

        continue

    # --------------------------------------------------
    # Sleep Command
    # --------------------------------------------------

    if "go to sleep" in command or "goodbye" in command:

        session.sleep()

        print("🤖 Ved: Going back to sleep.")

        continue

    # --------------------------------------------------
    # AI handles request
    # --------------------------------------------------

    reply = assistant.handle(command, session)

    print("🤖 Ved:", reply)