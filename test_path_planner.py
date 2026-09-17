from navigation.path_planner import pathPlanner


start = {

    "x": 2,

    "y": 3

}

goal = {

    "x": 12,

    "y": 9

}


path = pathPlanner.plan_path(

    start,

    goal,

    step_size=2

)

print()

print("Generated Path")

print()

for waypoint in path:

    print(waypoint)


print()

print("Following Path")

print()

while True:

    point = pathPlanner.next_waypoint()

    if point is None:

        break

    print("Move To:", point)