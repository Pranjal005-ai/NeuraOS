from voice.speech_listener import listen
from assistant import Assistant
from wakeword.detector import is_awake
from core.session import Session

assistant = Assistant()
session = Session()


print("=" * 50)
print("🤖 PROJECT VED STARTED")
print("=" * 50)

while True:

    print("\n🎤 Listening...")

    command = listen()

    if command == "":
        continue

    print("You:", command)

    # -----------------------------
    # Robot is sleeping
    # -----------------------------
    if not session.is_active():

        if is_awake(command):

            session.wake()

            print("🤖 Ved: Yes? How can I help you?")

        else:

            print("😴 Sleeping...")

        continue

    # -----------------------------
    # End conversation
    # -----------------------------
    if "go to sleep" in command or "goodbye" in command:

        session.sleep()

        print("🤖 Ved: Going back to sleep.")

        continue

    # -----------------------------
    # Handle user request
    # -----------------------------
    reply = assistant.handle(command, session)

    print("🤖 Ved:", reply)