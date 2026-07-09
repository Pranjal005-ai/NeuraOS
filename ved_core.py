from voice.speech_listener import listen
from voice.speaker import speak

from assistant import Assistant
from core.session import Session
import time


assistant = Assistant()
session = Session()

print("=" * 40)
print("VED AI CORE STARTED")
print("=" * 40)

while True:

    print("\n🎤 Speak...")

    command = listen()

    if not command:
        continue

    print("You:", command)

    print("➡️ Sending to Assistant...")
    reply = assistant.handle(command, session)
    print("⬅️ Assistant returned:", reply)

    print("Ved:", reply)

    speak(reply)

    # Wait before listening again
    time.sleep(0.7)

