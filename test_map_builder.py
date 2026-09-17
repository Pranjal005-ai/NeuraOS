from mapping.map_builder import mapBuilder
from mapping.landmark_manager import landmarkManager


# Create some landmarks

landmarkManager.add_landmark(120, 200)
landmarkManager.add_landmark(400, 150)
landmarkManager.add_landmark(250, 500)


pose = {

    "x": 12.5,

    "y": 7.2,

    "heading": 15.4

}


mapBuilder.add_frame(

    pose,

    landmarkManager.get_all()

)


print()

print("Frames:", mapBuilder.frame_count())

print()

print(mapBuilder.get_map())