import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic
from navigation import movement


car = Car.Car()
ultrasonic = Ultrasonic.UltrasonicScanner()


FRONT_BLOCKED_CM = 30

SIDE_DANGER_CM = 16
SIDE_CAUTION_CM = 22

FRONT_CLEAR_CM = 55

MAX_BYPASS_TIME = 4.0


def bypass_left():
    """
    Move around the obstacle on the left side.

    While bypassing, the ultrasonic mainly watches the left wall.
    It occasionally checks forward to see if the obstacle has been passed.
    """

    start_time = time.time()
    front_clear_count = 0

    while True:

        # Safety timeout so the car does not stay in bypass forever.
        if time.time() - start_time > MAX_BYPASS_TIME:
            car.stop()
            return

        # Look at the left wall.
        left_distance = ultrasonic.look_left()

        # If we are too close to the left wall,
        # move slightly away from it.
        if left_distance <= SIDE_DANGER_CM:

            car.diagonal_forward_right(110)

        # If we are getting close,
        # stop moving further left.
        elif left_distance <= SIDE_CAUTION_CM:

            car.forward(110)

        else:

            # Plenty of room on the left.
            car.diagonal_forward_left(120)

        time.sleep(0.08)

        # Check forward.
        front_distance = ultrasonic.look_forward()

        if front_distance >= FRONT_CLEAR_CM:

            front_clear_count += 1

        else:

            front_clear_count = 0

        # Do not trust one reading.
        if front_clear_count >= 2:

            car.stop()
            break


def bypass_right():
    """
    Move around the obstacle on the right side.

    While bypassing, the ultrasonic mainly watches the right wall.
    It occasionally checks forward to see if the obstacle has been passed.
    """

    start_time = time.time()
    front_clear_count = 0

    while True:

        if time.time() - start_time > MAX_BYPASS_TIME:
            car.stop()
            return

        right_distance = ultrasonic.look_right()

        # Too close to right wall.
        if right_distance <= SIDE_DANGER_CM:

            car.diagonal_forward_left(110)

        # Getting close to wall.
        elif right_distance <= SIDE_CAUTION_CM:

            car.forward(110)

        else:

            # Plenty of room on the right.
            car.diagonal_forward_right(120)

        time.sleep(0.08)

        # Check forward.
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
    Move slightly back toward the normal driving line
    after passing the obstacle.
    """

    if direction == "left":

        car.strafe_right(100)
        time.sleep(0.25)

    elif direction == "right":

        car.strafe_left(100)
        time.sleep(0.25)

    car.stop()

    ultrasonic.look_forward()


while True:

    # During normal driving the ultrasonic should already
    # be facing forward, so just read the distance.

    ultrasonic.look_forward()

    middle_distance = ultrasonic.get_stable_distance()

    print("Front:", middle_distance)

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

        print("Chosen direction:", direction)

        if direction == "left":

            bypass_left()

            recenter("left")

        elif direction == "right":

            bypass_right()

            recenter("right")

        else:

            # There is not enough space on either side.
            # Reverse slightly and scan again.
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

                # Still blocked.
                # Stop rather than blindly moving.
                car.stop()

                time.sleep(0.5)

    else:

        car.forward(140)

    time.sleep(0.02)