def follow_person(box, frame_width):

    x1, y1, x2, y2 = box

    center_x = (x1 + x2) / 2
    width = x2 - x1

    ratio = center_x / frame_width

    # Distance estimation
    if width > 380:
        return "STOP"

    if width < 140:
        return "MOVE_FORWARD"

    # Steering
    if ratio < 0.25:
        return "TURN_LEFT_FAST"

    elif ratio < 0.45:
        return "TURN_LEFT"

    elif ratio > 0.75:
        return "TURN_RIGHT_FAST"

    elif ratio > 0.55:
        return "TURN_RIGHT"

    else:
        return "FOLLOW"