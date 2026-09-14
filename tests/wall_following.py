import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic
from navigation import movement


car = Car.Car()
ultrasonic = Ultrasonic.UltrasonicScanner()


# --------------------------------------------------
# FRONT NAVIGATION
# --------------------------------------------------

FRONT_BLOCKED_CM = 25
FRONT_CLEAR_CM = 55


# --------------------------------------------------
# WALL FOLLOWING
# --------------------------------------------------

# Change this depending on which wall the robot
# should use as its reference.
WALL_SIDE = "left"
# WALL_SIDE = "right"


# The ultrasonic sensor is about 8 cm inward
# from the side of the car.
#
# If we want the BODY of the car to stay around
# 15 cm from the wall:
#
# 15 + 8 = 23 cm sensor reading.
TARGET_WALL_DISTANCE_CM = 23


# Allow a small range so the robot does not
# constantly move left/right.
WALL_TOLERANCE_CM = 3


# Wall following movement speeds.
WALL_FORWARD_SPEED = 140
WALL_CORRECTION_SPEED = 110


# --------------------------------------------------
# OBSTACLE BYPASS
# --------------------------------------------------

SIDE_DANGER_CM = 16
SIDE_CAUTION_CM = 22

MAX_BYPASS_TIME = 4.0


def follow_wall():
    """
    Keep the car approximately the desired distance
    from the selected wall.

    This is only used during normal forward driving.
    """

    if WALL_SIDE == "left":

        wall_distance = ultrasonic.look_left()

        print("Left wall:", wall_distance)

        too_close = (
            wall_distance
            < TARGET_WALL_DISTANCE_CM - WALL_TOLERANCE_CM
        )

        too_far = (
            wall_distance
            > TARGET_WALL_DISTANCE_CM + WALL_TOLERANCE_CM
        )

        if too_close:

            # Left wall is too close.
            # Move slightly away from it.
            car.diagonal_forward_right(
                WALL_CORRECTION_SPEED
            )

        elif too_far:

            # Left wall is too far away.
            # Move slightly toward it.
            car.diagonal_forward_left(
                WALL_CORRECTION_SPEED
            )

        else:

            # Distance from wall is good.
            car.forward(
                WALL_FORWARD_SPEED
            )


    elif WALL_SIDE == "right":

        wall_distance = ultrasonic.look_right()

        print("Right wall:", wall_distance)

        too_close = (
            wall_distance
            < TARGET_WALL_DISTANCE_CM - WALL_TOLERANCE_CM
        )

        too_far = (
            wall_distance
            > TARGET_WALL_DISTANCE_CM + WALL_TOLERANCE_CM
        )

        if too_close:

            # Right wall is too close.
            # Move slightly away from it.
            car.diagonal_forward_left(
                WALL_CORRECTION_SPEED
            )

        elif too_far:

            # Right wall is too far away.
            # Move slightly toward it.
            car.diagonal_forward_right(
                WALL_CORRECTION_SPEED
            )

        else:

            # Distance from wall is good.
            car.forward(
                WALL_FORWARD_SPEED
            )

    else:

        # Invalid WALL_SIDE value.
        # Just drive forward safely.
        car.forward(
            WALL_FORWARD_SPEED
        )

    # Always return the sensor forward after
    # checking the wall.
    ultrasonic.look_forward()


def bypass_left():
    """
    Move around the obstacle on the left side.
    """

    start_time = time.time()
    front_clear_count = 0

    while True:

        if time.time() - start_time > MAX_BYPASS_TIME:
            car.stop()
            return

        left_distance = ultrasonic.look_left()

        if left_distance <= SIDE_DANGER_CM:

            car.diagonal_forward_right(110)

        elif left_distance <= SIDE_CAUTION_CM:

            car.forward(110)

        else:

            car.diagonal_forward_left(120)

        time.sleep(0.08)

        front_distance = ultrasonic.look_forward()

        if front_distance >= FRONT_CLEAR_CM:

            front_clear_count += 1

        else:

            front_clear_count = 0

        if front_clear_count >= 2:

            car.stop()
            break


def bypass_right():
    """
    Move around the obstacle on the right side.
    """

    start_time = time.time()
    front_clear_count = 0

    while True:

        if time.time() - start_time > MAX_BYPASS_TIME:
            car.stop()
            return

        right_distance = ultrasonic.look_right()

        if right_distance <= SIDE_DANGER_CM:

            car.diagonal_forward_left(110)

        elif right_distance <= SIDE_CAUTION_CM:

            car.forward(110)

        else:

            car.diagonal_forward_right(120)

        time.sleep(0.08)

        front_distance = ultrasonic.look_forward()

        if front_distance >= FRONT_CLEAR_CM:

            front_clear_count += 1

        else:

            front_clear_count = 0

        if front_clear_count >= 2:

            car.stop()
            break


def recenter(direction):
    """
    Move slightly back toward the normal driving
    line after passing the obstacle.
    """

    if direction == "left":

        car.strafe_right(100)
        time.sleep(0.25)

    elif direction == "right":

        car.strafe_left(100)
        time.sleep(0.25)

    car.stop()

    ultrasonic.look_forward()


# Make sure ultrasonic starts facing forward.
ultrasonic.look_forward()


while True:

    # --------------------------------------------------
    # 1. CHECK FRONT
    # --------------------------------------------------

    middle_distance = ultrasonic.get_stable_distance()

    print("Front:", middle_distance)


    # --------------------------------------------------
    # 2. OBSTACLE DETECTED
    # --------------------------------------------------

    if middle_distance <= FRONT_BLOCKED_CM:

        car.stop()

        time.sleep(0.1)

        scan = ultrasonic.scan_all()

        front = scan["front"]
        left = scan["left"]
        right = scan["right"]

        print(
            "Front:",
            front,
            "Left:",
            left,
            "Right:",
            right
        )

        direction = movement.get_direction(
            left,
            right
        )

        print(
            "Chosen direction:",
            direction
        )


        if direction == "left":

            bypass_left()

            recenter("left")


        elif direction == "right":

            bypass_right()

            recenter("right")


        else:

            # There is not enough room on either side.
            car.backward(120)

            time.sleep(0.4)

            car.stop()

            time.sleep(0.2)

            scan = ultrasonic.scan_all()

            left = scan["left"]
            right = scan["right"]

            direction = movement.get_direction(
                left,
                right
            )


            if direction == "left":

                bypass_left()

                recenter("left")


            elif direction == "right":

                bypass_right()

                recenter("right")


            else:

                car.stop()

                time.sleep(0.5)


    # --------------------------------------------------
    # 3. FRONT CLEAR - WALL FOLLOW
    # --------------------------------------------------

    else:

        follow_wall()


    time.sleep(0.02)