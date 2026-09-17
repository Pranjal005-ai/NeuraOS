from mapping.map_builder import mapBuilder
from mapping.map_storage import mapStorage
from mapping.landmark_manager import landmarkManager


# -----------------------------
# Add landmarks
# -----------------------------

landmarkManager.add_landmark(120, 200)
landmarkManager.add_landmark(350, 500)

# -----------------------------
# Robot pose
# -----------------------------

pose = {

    "x": 15,

    "y": 7,

    "heading": 23

}

# -----------------------------
# Build map
# -----------------------------

mapBuilder.add_frame(

    pose,

    landmarkManager.get_all()

)

# -----------------------------
# Save
# -----------------------------

mapStorage.save(

    "office",

    mapBuilder.get_map()

)

print()

print("Saved Maps:")

print(

    mapStorage.list_maps()

)

print()

loaded = mapStorage.load(

    "office"

)

print()

print("Loaded Map:")

print(

    loaded

)