from ai.brain import Brain

brain = Brain()

while True:

    cmd = input("You: ")

    print(brain.process_command(cmd))
    