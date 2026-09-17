import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic

from libs import ACB_Canmv

from navigation.vision import PillarVision
from navigation.lane import LaneFollower


# ==================================================
# HARDWARE
# ==================================================

car = Car.Car()

ultrasonic = Ultrasonic.UltrasonicScanner()

cam = ACB_Canmv.ACB_Canmv()

cam.init(
    cam.SDA,
    cam.SCL
)

time.sleep_ms(500)


# ==================================================
# NAVIGATION
# ==================================================

vision = PillarVision(
    cam,
    red_index=1,
    green_index=2,
    pixels_threshold=200,
    area_threshold=200
)

lane = LaneFollower(car)


# ==================================================
# STATES
# ==================================================

FOLLOW_LANE = 0

APPROACH_PILLAR = 1

PASS_PILLAR = 2

RECENTER = 3


state = FOLLOW_LANE


# ==================================================
# SETTINGS
# ==================================================

# When the ultrasonic sees something this close
# while we have a confirmed colour, begin passing.

PILLAR_TRIGGER_CM = 30


# Emergency protection.

EMERGENCY_DISTANCE_CM = 12


# Existing bypass settings.

SIDE_DANGER_CM = 16

SIDE_CAUTION_CM = 22

FRONT_CLEAR_CM = 55

MAX_BYPASS_TIME_MS = 4000


# Camera positioning.

# These are initial values only.
# Calibrate using the real camera image.

RED_TARGET_X = 105

GREEN_TARGET_X = 215

X_TOLERANCE = 15


# Periodic front check while lane following.

FRONT_CHECK_INTERVAL_MS = 2000

last_front_check = time.ticks_ms()


# Current pillar being handled.

active_pillar = None


# ==================================================
# BYPASS LEFT
# ==================================================

def bypass_left():

    start_time = time.ticks_ms()

    front_clear_count = 0


    while True:

        elapsed = time.ticks_diff(
            time.ticks_ms(),
            start_time
        )


        if elapsed > MAX_BYPASS_TIME_MS:

            car.stop()

            return


        # Watch the LEFT side while passing.

        left_distance = ultrasonic.look_left()


        if left_distance <= SIDE_DANGER_CM:

            car.diagonal_forward_right(110)


        elif left_distance <= SIDE_CAUTION_CM:

            car.forward(110)


        else:

            car.diagonal_forward_left(120)


        time.sleep(0.08)


        # Periodically verify that the path
        # in front has opened.

        front_distance = ultrasonic.look_forward()


        if front_distance >= FRONT_CLEAR_CM:

            front_clear_count += 1

        else:

            front_clear_count = 0


        if front_clear_count >= 2:

            car.stop()

            return


# ==================================================
# BYPASS RIGHT
# ==================================================

def bypass_right():

    start_time = time.ticks_ms()

    front_clear_count = 0


    while True:

        elapsed = time.ticks_diff(
            time.ticks_ms(),
            start_time
        )


        if elapsed > MAX_BYPASS_TIME_MS:

            car.stop()

            return


        # Watch the RIGHT side while passing.

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

            return


# ==================================================
# RECENTER
# ==================================================

def recenter(direction):

    if direction == "left":

        car.strafe_right(100)

        time.sleep(0.25)


    elif direction == "right":

        car.strafe_left(100)

        time.sleep(0.25)


    car.stop()


# ==================================================
# APPROACH PILLAR
# ==================================================

def approach_pillar(color):
    """
    Camera controls the early positioning.

    RED:
        pillar should move toward LEFT side
        of image because we pass on its RIGHT.

    GREEN:
        pillar should move toward RIGHT side
        of image because we pass on its LEFT.
    """

    cx = vision.cx


    # ----------------------------------------------
    # RED
    # ----------------------------------------------

    if color == "red":

        if cx > RED_TARGET_X + X_TOLERANCE:

            car.diagonal_forward_right(105)

        else:

            car.forward(115)


    # ----------------------------------------------
    # GREEN
    # ----------------------------------------------

    elif color == "green":

        if cx < GREEN_TARGET_X - X_TOLERANCE:

            car.diagonal_forward_left(105)

        else:

            car.forward(115)


# ==================================================
# INITIAL POSITION
# ==================================================

# Start with ultrasonic looking right because
# normal navigation follows the right wall.

ultrasonic.look_right()


print("Muchengeti ready")


# ==================================================
# MAIN LOOP
# ==================================================

while True:


    # ==================================================
    # STATE 1
    # FOLLOW LANE
    # ==================================================

    if state == FOLLOW_LANE:


        # ------------------------------------------
        # CAMERA
        # ------------------------------------------

        detected_color = vision.update()


        # A valid pillar has been confirmed.

        if detected_color is not None:

            active_pillar = detected_color

            print(
                "LOCKED:",
                active_pillar,
                "CX:",
                vision.cx,
                "W:",
                vision.width,
                "H:",
                vision.height
            )


            state = APPROACH_PILLAR

            continue


        # ------------------------------------------
        # RIGHT WALL FOLLOWING
        # ------------------------------------------

        right_distance = (
            ultrasonic.get_stable_distance()
        )


        action = lane.follow_right_wall(
            right_distance
        )


        print(
            "LANE",
            "Right:",
            right_distance,
            "Action:",
            action
        )


        # ------------------------------------------
        # PERIODIC FRONT SAFETY CHECK
        # ------------------------------------------

        now = time.ticks_ms()


        if time.ticks_diff(
            now,
            last_front_check
        ) >= FRONT_CHECK_INTERVAL_MS:


            front_distance = (
                ultrasonic.look_forward()
            )


            print(
                "Front check:",
                front_distance
            )


            # Emergency protection only.
            #
            # Do NOT randomly choose left/right.

            if front_distance <= EMERGENCY_DISTANCE_CM:

                car.stop()

                print(
                    "Emergency object ahead"
                )


            # Return sensor to lane-following wall.

            ultrasonic.look_right()


            last_front_check = now


    # ==================================================
    # STATE 2
    # APPROACH CONFIRMED PILLAR
    # ==================================================

    elif state == APPROACH_PILLAR:


        # ------------------------------------------
        # LOOK FOR THE SAME COLOUR
        # ------------------------------------------

        if active_pillar == "red":

            detected = cam.color_recognize(
                vision.red_index,
                vision.pixels_threshold,
                vision.area_threshold
            )


        elif active_pillar == "green":

            detected = cam.color_recognize(
                vision.green_index,
                vision.pixels_threshold,
                vision.area_threshold
            )


        else:

            detected = False


        # ------------------------------------------
        # UPDATE CAMERA POSITION
        # ------------------------------------------

        if detected:

            width = cam.getW
            height = cam.getH

            area = width * height


            # Ignore tiny colour noise.

            if (
                width >= vision.min_width
                and
                height >= vision.min_height
                and
                area >= vision.min_area
            ):

                vision.cx = cam.getCX
                vision.cy = cam.getCY

                vision.width = width
                vision.height = height

                vision.last_seen = (
                    time.ticks_ms()
                )


                print(
                    "TRACKING",
                    active_pillar,
                    "CX:",
                    vision.cx,
                    "W:",
                    vision.width,
                    "H:",
                    vision.height
                )


        # ------------------------------------------
        # CAMERA CONTROLS POSITION
        # ------------------------------------------

        approach_pillar(
            active_pillar
        )


        # ------------------------------------------
        # FRONT DISTANCE
        # ------------------------------------------
        #
        # Now we want ultrasonic confirmation
        # that the identified object is physically
        # close.
        #
        # Move ultrasonic forward.

        front_distance = (
            ultrasonic.look_forward()
        )


        print(
            "PILLAR:",
            active_pillar,
            "Front:",
            front_distance
        )


        # ------------------------------------------
        # OBJECT CLOSE
        # ------------------------------------------

        if front_distance <= PILLAR_TRIGGER_CM:

            car.stop()


            print(
                "Ultrasonic confirmed object:",
                front_distance,
                "cm"
            )


            print(
                "Camera says:",
                active_pillar
            )


            state = PASS_PILLAR


    # ==================================================
    # STATE 3
    # PASS PILLAR
    # ==================================================

    elif state == PASS_PILLAR:


        # ------------------------------------------
        # RED
        # ------------------------------------------

        if active_pillar == "red":

            print(
                "RED -> PASS RIGHT"
            )


            bypass_right()


        # ------------------------------------------
        # GREEN
        # ------------------------------------------

        elif active_pillar == "green":

            print(
                "GREEN -> PASS LEFT"
            )


            bypass_left()


        state = RECENTER


    # ==================================================
    # STATE 4
    # RECENTER
    # ==================================================

    elif state == RECENTER:


        if active_pillar == "red":

            recenter("right")


        elif active_pillar == "green":

            recenter("left")


        # We have finished with this pillar.

        vision.clear()

        active_pillar = None


        # Return ultrasonic to the right wall.

        ultrasonic.look_right()


        last_front_check = (
            time.ticks_ms()
        )


        print(
            "Pillar complete"
        )


        print(
            "Returning to lane following"
        )


        state = FOLLOW_LANE


    time.sleep_ms(20)