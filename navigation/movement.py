MIN_PASS_DISTANCE = 25

SENSOR_TO_CAR_SIDE_CM = 8


def get_direction(left_distance, right_distance):
    """
    Decide which side has enough space for the car to pass.

    The ultrasonic sensor is about 8 cm inward from the
    outside edge of the car.

    For now we use the raw sensor distance and require
    at least 25 cm before trying to pass on that side.
    """

    left_safe = left_distance >= MIN_PASS_DISTANCE
    right_safe = right_distance >= MIN_PASS_DISTANCE

    # Both sides have enough room.
    # Use the side with more space.
    if left_safe and right_safe:

        if left_distance > right_distance:
            return "left"

        return "right"

    # Only the left side has enough room.
    if left_safe:
        return "left"

    # Only the right side has enough room.
    if right_safe:
        return "right"

    # Neither side has enough room.
    return "blocked"