import time


# --------------------------------------------------
# PARKING SETTINGS
# --------------------------------------------------

PARKING_OPEN_DISTANCE_CM = 45

# Distance from the wall when fully parked.
PARKED_WALL_DISTANCE_CM = 15

PARKING_TOLERANCE_CM = 3


PARK_FORWARD_SPEED = 90
PARK_REVERSE_SPEED = 80
PARK_STRAFE_SPEED = 80


# Time used to position the car beside the bay.
#
# These values MUST be calibrated on the real robot.
FORWARD_ALIGN_TIME = 0.45
REVERSE_ALIGN_TIME = 0.25

# Safety limit when strafing into the parking space.
MAX_STRAFE_TIME = 2.0


def find_parking_space(car, ultrasonic, parking_side="right"):
    """
    Drive forward and look for a large opening beside the car.

    Returns True when a possible parking space is found.
    """

    print("Looking for parking space on:", parking_side)

    while True:

        if parking_side == "right":

            distance = ultrasonic.look_right()

        else:

            distance = ultrasonic.look_left()


        print(
            "Parking side distance:",
            distance
        )


        # Large side distance means there may be an opening.
        if distance >= PARKING_OPEN_DISTANCE_CM:

            car.stop()

            print("Possible parking space found")

            return True


        car.forward(
            PARK_FORWARD_SPEED
        )

        time.sleep(0.05)


def move_beside_space(car, ultrasonic):
    """
    Move forward slightly so the car body is positioned
    alongside the parking bay.
    """

    print("Positioning beside parking space")

    ultrasonic.look_forward()

    car.forward(
        PARK_FORWARD_SPEED
    )

    time.sleep(
        FORWARD_ALIGN_TIME
    )

    car.stop()

    time.sleep(0.2)


def reverse_for_entry(car):
    """
    Reverse slightly before moving sideways into the bay.
    """

    print("Preparing parking entry")

    car.backward(
        PARK_REVERSE_SPEED
    )

    time.sleep(
        REVERSE_ALIGN_TIME
    )

    car.stop()

    time.sleep(0.2)


def strafe_into_space(
    car,
    ultrasonic,
    parking_side="right"
):
    """
    Move sideways into the parking space.

    The ultrasonic watches the parking-side wall.
    """

    print(
        "Entering parking space:",
        parking_side
    )

    start_time = time.time()


    while True:

        # ------------------------------------------
        # SAFETY TIMEOUT
        # ------------------------------------------

        if (
            time.time() - start_time
            >= MAX_STRAFE_TIME
        ):

            print(
                "Parking timeout"
            )

            car.stop()

            return False


        # ------------------------------------------
        # READ PARKING WALL
        # ------------------------------------------

        if parking_side == "right":

            distance = ultrasonic.look_right()

        else:

            distance = ultrasonic.look_left()


        print(
            "Parking wall:",
            distance
        )


        # ------------------------------------------
        # TARGET REACHED
        # ------------------------------------------

        if (
            distance
            <= PARKED_WALL_DISTANCE_CM
            + PARKING_TOLERANCE_CM
        ):

            car.stop()

            print(
                "Parking depth reached"
            )

            return True


        # ------------------------------------------
        # CONTINUE INTO SPACE
        # ------------------------------------------

        if parking_side == "right":

            car.strafe_right(
                PARK_STRAFE_SPEED
            )

        else:

            car.strafe_left(
                PARK_STRAFE_SPEED
            )


        time.sleep(0.05)


def adjust_parking_position(
    car,
    ultrasonic,
    parking_side="right"
):
    """
    Make one small adjustment if the car ended
    too close or too far from the wall.
    """

    if parking_side == "right":

        distance = ultrasonic.look_right()

    else:

        distance = ultrasonic.look_left()


    print(
        "Final parking distance:",
        distance
    )


    minimum = (
        PARKED_WALL_DISTANCE_CM
        - PARKING_TOLERANCE_CM
    )

    maximum = (
        PARKED_WALL_DISTANCE_CM
        + PARKING_TOLERANCE_CM
    )


    # ----------------------------------------------
    # TOO CLOSE
    # ----------------------------------------------

    if distance < minimum:

        print(
            "Too close - moving away"
        )

        if parking_side == "right":

            car.strafe_left(60)

        else:

            car.strafe_right(60)


        time.sleep(0.12)

        car.stop()


    # ----------------------------------------------
    # TOO FAR
    # ----------------------------------------------

    elif distance > maximum:

        print(
            "Too far - moving closer"
        )

        if parking_side == "right":

            car.strafe_right(60)

        else:

            car.strafe_left(60)


        time.sleep(0.12)

        car.stop()


def parallel_park(
    car,
    ultrasonic,
    parking_side="right"
):
    """
    Complete parallel parking routine.
    """

    print("----------------------")
    print("STARTING PARALLEL PARK")
    print("----------------------")


    # ----------------------------------------------
    # 1. FIND PARKING AREA
    # ----------------------------------------------

    found = find_parking_space(
        car,
        ultrasonic,
        parking_side
    )

    if not found:

        return False


    # ----------------------------------------------
    # 2. POSITION CAR BESIDE BAY
    # ----------------------------------------------

    move_beside_space(
        car,
        ultrasonic
    )


    # ----------------------------------------------
    # 3. SMALL REVERSE
    # ----------------------------------------------

    reverse_for_entry(
        car
    )


    # ----------------------------------------------
    # 4. MOVE INTO PARKING BAY
    # ----------------------------------------------

    parked = strafe_into_space(
        car,
        ultrasonic,
        parking_side
    )

    if not parked:

        car.stop()

        return False


    # ----------------------------------------------
    # 5. FINAL POSITION CORRECTION
    # ----------------------------------------------

    adjust_parking_position(
        car,
        ultrasonic,
        parking_side
    )


    # ----------------------------------------------
    # 6. FINISHED
    # ----------------------------------------------

    car.stop()

    ultrasonic.look_forward()

    print("----------------------")
    print("PARKING COMPLETE")
    print("----------------------")

    return True