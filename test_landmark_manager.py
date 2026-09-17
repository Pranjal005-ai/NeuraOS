from mapping.landmark_manager import landmarkManager

id1 = landmarkManager.add_landmark(100, 220)

id2 = landmarkManager.add_landmark(320, 410)

print(landmarkManager.get_all())

landmarkManager.update_landmark(
    id1,
    120,
    240
)

print()

print(landmarkManager.get_all())