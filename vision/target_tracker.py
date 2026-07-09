TARGET = None

def lock_target(name):

    global TARGET

    TARGET = name

    print(f"🔒 Locked on {name}")


def unlock_target():

    global TARGET

    TARGET = None

    print("🔓 Target Released")


def get_target():

    return TARGET