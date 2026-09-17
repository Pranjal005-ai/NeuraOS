from navigation.path_planner import pathPlanner
from navigation.path_follower import pathFollower


start = {

    "x": 0,

    "y": 0

}

goal = {

    "x": 5,

    "y": 5

}


path = pathPlanner.plan_path(

    start,

    goal,

    step_size=1

)

print("PATH:")
for p in path:
    print(p)

pathFollower.set_path(path)


pose = {

    "x": 0,

    "y": 0,

    "heading": 0

}


while not pathFollower.finished():

    result = pathFollower.update(

        pose

    )

    print(result)

    command = result["command"]

    if command == "TURN_LEFT":

        pose["heading"] += 15

    elif command == "TURN_RIGHT":

        pose["heading"] -= 15

    elif command == "FORWARD":

        print("Before:", pose)

        pose["x"] += 0.5
        pose["y"] += 0.5

        print("After :", pose)

        pose["x"] += 0.5

        pose["y"] += 0.5

    elif command == "WAYPOINT_REACHED":

        print("Reached waypoint")

print()

print("Destination reached!")