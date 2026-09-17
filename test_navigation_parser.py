from navigation.parser import navigationParser

tests = [

    "Go to room 205",

    "Take me to reception",

    "Navigate to kitchen",

    "Return to charging station",

    "Go home"

]

for command in tests:

    print(command)

    print("Destination:", navigationParser.extractDestination(command))

    print()