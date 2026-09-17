from navigation.localization import localization
from mapping.map_builder import mapBuilder


# -------------------------------
# Build Sample Map
# -------------------------------

mapBuilder.clear()

mapBuilder.add_frame(

    {

        "x": 0,
        "y": 0,
        "heading": 0

    },

    {}

)

mapBuilder.add_frame(

    {

        "x": 5,
        "y": 2,
        "heading": 10

    },

    {}

)

mapBuilder.add_frame(

    {

        "x": 12,
        "y": 8,
        "heading": 20

    },

    {}

)

saved_map = mapBuilder.get_map()

# -------------------------------
# Load Map
# -------------------------------

localization.load_map(

    saved_map

)

# -------------------------------
# Current Robot Pose
# -------------------------------

current_pose = {

    "x": 4.7,

    "y": 2.1,

    "heading": 12

}

localization.update_pose(

    current_pose

)

# -------------------------------
# Localize
# -------------------------------

result = localization.localize()

print()

print("Localization Result")

print(result)