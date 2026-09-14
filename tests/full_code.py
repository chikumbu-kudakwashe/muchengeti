import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic

from navigation import movement
from libs import ACB_Canmv


# --------------------------------------------------
# HARDWARE
# --------------------------------------------------

car = Car.Car()
ultrasonic = Ultrasonic.UltrasonicScanner()

cam = ACB_Canmv.ACB_Canmv()

cam.init(
    cam.SDA,
    cam.SCL
)

time.sleep_ms(500)


# --------------------------------------------------
# CAMERA SETTINGS
# --------------------------------------------------

RED_INDEX = 1
GREEN_INDEX = 2

PIXELS_TH = 200
AREA_TH = 200


# The camera alternates between checking red
# and checking green.
camera_color = "red"


# Remember the last traffic colour seen.
last_traffic_color = None
last_color_time = 0


# Keep the colour for a short time after detection.
COLOR_MEMORY_MS = 700


# Only perform the traffic maneuver when the robot
# is reasonably close to something in front.
TRAFFIC_ACTION_DISTANCE_CM = 55


# --------------------------------------------------
# ULTRASONIC SETTINGS
# --------------------------------------------------

FRONT_BLOCKED_CM = 25

SIDE_DANGER_CM = 16
SIDE_CAUTION_CM = 22

FRONT_CLEAR_CM = 55

MAX_BYPASS_TIME = 4.0


# --------------------------------------------------
# CAMERA
# --------------------------------------------------

def detect_traffic_color():
    """
    Check one traffic colour at a time.

    Red and green are alternated between control loops
    instead of switching modes multiple times in one loop.
    """

    global camera_color
    global last_traffic_color
    global last_color_time


    if camera_color == "red":

        detected = cam.color_recognize(
            RED_INDEX,
            PIXELS_TH,
            AREA_TH
        )

        camera_color = "green"

        if detected:

            last_traffic_color = "red"
            last_color_time = time.ticks_ms()

            print("RED pillar detected")

            print(
                "X,Y,W,H:",
                cam.getX,
                cam.getY,
                cam.getW,
                cam.getH
            )


    else:

        detected = cam.color_recognize(
            GREEN_INDEX,
            PIXELS_TH,
            AREA_TH
        )

        camera_color = "red"

        if detected:

            last_traffic_color = "green"
            last_color_time = time.ticks_ms()

            print("GREEN pillar detected")

            print(
                "X,Y,W,H:",
                cam.getX,
                cam.getY,
                cam.getW,
                cam.getH
            )


def get_traffic_color():
    """
    Return the recently detected traffic colour.

    The short memory prevents us from losing the colour
    immediately when the camera switches recognition mode.
    """

    if last_traffic_color is None:
        return None

    elapsed = time.ticks_diff(
        time.ticks_ms(),
        last_color_time
    )

    if elapsed <= COLOR_MEMORY_MS:
        return last_traffic_color

    return None


# --------------------------------------------------
# OBSTACLE BYPASS
# --------------------------------------------------

def bypass_left():
    """
    Pass an obstacle on its left side.
    """

    start_time = time.time()
    front_clear_count = 0

    while True:

        if time.time() - start_time > MAX_BYPASS_TIME:

            car.stop()

            return


        left_distance = ultrasonic.look_left()


        # Too close to the left wall.
        if left_distance <= SIDE_DANGER_CM:

            car.diagonal_forward_right(110)


        # Safe enough to continue straight.
        elif left_distance <= SIDE_CAUTION_CM:

            car.forward(110)


        # Enough room to move further left.
        else:

            car.diagonal_forward_left(120)


        time.sleep(0.08)


        # Check if the obstacle has been passed.
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
    Pass an obstacle on its right side.
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


        # Safe enough to continue straight.
        elif right_distance <= SIDE_CAUTION_CM:

            car.forward(110)


        # Enough room to move further right.
        else:

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


# --------------------------------------------------
# RECENTER
# --------------------------------------------------

def recenter(direction):
    """
    Move back toward the normal driving line
    after passing the pillar or obstacle.
    """

    if direction == "left":

        car.strafe_right(100)

        time.sleep(0.25)


    elif direction == "right":

        car.strafe_left(100)

        time.sleep(0.25)


    car.stop()

    ultrasonic.look_forward()


# --------------------------------------------------
# TRAFFIC RULE HANDLING
# --------------------------------------------------

def handle_traffic_pillar(color):
    """
    Apply WRO traffic pillar rules.

    RED:
        keep right
        pass pillar on right

    GREEN:
        keep left
        pass pillar on left
    """

    global last_traffic_color


    if color == "red":

        print("RED -> KEEP RIGHT")

        bypass_right()

        recenter("right")


    elif color == "green":

        print("GREEN -> KEEP LEFT")

        bypass_left()

        recenter("left")


    # Forget the pillar after completing the maneuver
    # so it does not immediately trigger again.
    last_traffic_color = None


# --------------------------------------------------
# START
# --------------------------------------------------

ultrasonic.look_forward()


while True:

    # --------------------------------------------------
    # 1. CAMERA CHECK
    # --------------------------------------------------

    detect_traffic_color()

    traffic_color = get_traffic_color()


    # --------------------------------------------------
    # 2. FRONT DISTANCE
    # --------------------------------------------------

    ultrasonic.look_forward()

    middle_distance = ultrasonic.get_stable_distance()

    print(
        "Front:",
        middle_distance,
        "Traffic:",
        traffic_color
    )


    # --------------------------------------------------
    # 3. TRAFFIC PILLAR
    # --------------------------------------------------

    if (
        traffic_color is not None
        and middle_distance <= TRAFFIC_ACTION_DISTANCE_CM
    ):

        car.stop()

        time.sleep(0.1)

        handle_traffic_pillar(
            traffic_color
        )


    # --------------------------------------------------
    # 4. UNKNOWN OBSTACLE
    # --------------------------------------------------

    elif middle_distance <= FRONT_BLOCKED_CM:

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


        # No colour was detected.
        # Use the original ultrasonic decision.
        direction = movement.get_direction(
            left,
            right
        )


        print(
            "Ultrasonic direction:",
            direction
        )


        if direction == "left":

            bypass_left()

            recenter("left")


        elif direction == "right":

            bypass_right()

            recenter("right")


        else:

            # Both sides blocked.
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
    # 5. NORMAL DRIVING
    # --------------------------------------------------

    else:

        car.forward(140)


    time.sleep(0.02)