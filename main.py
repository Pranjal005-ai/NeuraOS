from voice.speech_listener import listen
from motion.motor_controller import *
from ai.chatgpt import ask_ai

print("====================================")
print("      AI Robot Started")
print("====================================")

while True:

    print("\nWaiting for your command...")

    command = listen()

    if command == "":
        continue

    print("You:", command)

    reply = ask_ai(command)

    print("AI:", reply)

    if "forward" in command:
        forward()

    elif "back" in command:
        backward()

    elif "left" in command:
        left()

    elif "right" in command:
        right()

    elif "stop" in command:
        stop()