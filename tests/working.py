import time

import hardware.car as Car
import hardware.ultrasonic as Ultrasonic

from libs import ACB_Canmv
from navigation.track import TrackFollower


# ==================================================
# HARDWARE
# ==================================================

car = Car.Car()
ultrasonic = Ultrasonic.UltrasonicScanner()

cam = ACB_Canmv.ACB_Canmv()
cam.init(cam.SDA, cam.SCL)

time.sleep_ms(500)

track = TrackFollower(car)


# ==================================================
# STATES
# ==================================================

FOLLOW_TRACK = 0
APPROACH_CORNER = 1
TURNING = 2
TRACK_RECOVERY = 3

state = FOLLOW_TRACK


# ==================================================
# DISTANCE SETTINGS
# ==================================================

# Start slowing down when the front wall is this close.
WALL_DETECT_CM = 40

# Start the actual turn at this distance.
TURN_TRIGGER_CM = 25

# Emergency backup trigger.
EMERGENCY_CM = 10


# ==================================================
# TURN COMPLETION SETTINGS
# ==================================================

# While turning, first confirm that the ultrasonic
# has actually seen the old wall at close range.
TURN_WALL_CLOSE_CM = 18

# After that close wall has been seen, when the
# distance grows beyond this value we assume the
# car has turned far enough away from the old wall.
TURN_WALL_RELEASE_CM = 28

# Safety net so a corner can never spin forever if the
# ultrasonic never sees the expected close/release pattern.
TURN_TIMEOUT_MS = 2500


# ==================================================
# SPEED SETTINGS
# ==================================================

CORNER_APPROACH_SPEED = 85

CORNER_TURN_SPEED = 105

RECOVERY_FORWARD_SPEED = 85

RECOVERY_CORRECTION_SPEED = 70

CORNER_EXIT_SPEED = 95


# ==================================================
# CAMERA SETTINGS
# ==================================================

TRACK_CENTER_TOLERANCE = 8


# ==================================================
# RECOVERY SETTINGS
# ==================================================

# Move forward for at least this long after turning
# before fully trusting the new track position.
RECOVERY_MIN_FORWARD_MS = 250

# Don't drive forward forever if the track is not found.
RECOVERY_TIMEOUT_MS = 1800


# ==================================================
# TURN DIRECTION
# ==================================================
#
# Set this based on the direction around the track.
#
# "left"  -> left-hand corners
# "right" -> right-hand corners

TURN_DIRECTION = "left"


# ==================================================
# ULTRASONIC
# ==================================================

ULTRASONIC_INTERVAL_MS = 120

last_ultrasonic_check = time.ticks_ms()

front_distance = 999


# ==================================================
# LAP LEARNING
# ==================================================

lap = 1

corner_count = 0

CORNERS_PER_LAP = 4

track_memory = []

straight_started_ms = time.ticks_ms()


# ==================================================
# STATE DATA
# ==================================================

turn_saw_close_wall = False

turn_started_ms = 0

recovery_started_ms = 0


# ==================================================
# CAMERA
# ==================================================

def read_track():
    """
    Read visual patrol data from the K210 camera.

    Returns:
        True, error
        False, 0
    """

    if cam.visual_patrol():

        error = cam.Visual_data

        return True, error

    return False, 0


# ==================================================
# ULTRASONIC
# ==================================================

def update_front_distance():
    """
    Periodic ultrasonic update during normal driving.
    """

    global front_distance
    global last_ultrasonic_check

    now = time.ticks_ms()

    if time.ticks_diff(
        now,
        last_ultrasonic_check
    ) >= ULTRASONIC_INTERVAL_MS:

        front_distance = (
            ultrasonic.get_stable_distance()
        )

        last_ultrasonic_check = now

        print(
            "Front:",
            front_distance,
            "cm"
        )

    return front_distance


# ==================================================
# CORNER MOVEMENT
# ==================================================

def drive_corner():
    """
    Rotate the car in place toward the known corner
    direction.

    The ultrasonic is fixed facing forward, so rotating
    in place sweeps it away from the old wall and toward
    the new straight. The TURNING state below watches
    that sweep to decide when the corner is finished.
    """

    if TURN_DIRECTION == "left":

        car.rotate_left(
            CORNER_TURN_SPEED
        )

    else:

        car.rotate_right(
            CORNER_TURN_SPEED
        )


# ==================================================
# RECORD CORNER
# ==================================================

def record_corner():
    global straight_started_ms

    now = time.ticks_ms()

    straight_time = time.ticks_diff(
        now,
        straight_started_ms
    )

    if lap == 1:

        track_memory.append(
            {
                "corner": corner_count + 1,
                "straight_time_ms": straight_time,
                "wall_distance": front_distance
            }
        )

        print(
            "LEARNED CORNER",
            corner_count + 1,
            "Straight:",
            straight_time,
            "ms",
            "Wall:",
            front_distance,
            "cm"
        )


# ==================================================
# LAP COMPLETE
# ==================================================

def complete_lap():
    global lap

    lap += 1

    print("")
    print("==============================")
    print(
        "LAP",
        lap - 1,
        "COMPLETE"
    )
    print("==============================")

    if lap == 2:

        print("Track learned.")
        print("Increasing straight speed.")
        print(
            "Memory:",
            track_memory
        )

    print(
        "Starting lap:",
        lap
    )

    print("")


# ==================================================
# FINISH CORNER
# ==================================================

def finish_corner():
    global corner_count
    global straight_started_ms
    global state
    global turn_saw_close_wall

    corner_count += 1

    print("")
    print(
        "CORNER COMPLETE:",
        corner_count
    )

    if corner_count >= CORNERS_PER_LAP:

        corner_count = 0

        complete_lap()

    straight_started_ms = (
        time.ticks_ms()
    )

    turn_saw_close_wall = False

    state = FOLLOW_TRACK


# ==================================================
# START
# ==================================================

car.stop()

time.sleep_ms(500)

print("")
print("==============================")
print("MUCHENGETI TRACK NAVIGATION")
print("==============================")
print("")

print(
    "Camera = primary navigation"
)

print(
    "Ultrasonic = wall / turn confirmation"
)

print(
    "Turn direction:",
    TURN_DIRECTION
)

print(
    "Lap:",
    lap
)

print("")


# ==================================================
# MAIN LOOP
# ==================================================

while True:


    # ==================================================
    # FOLLOW TRACK
    # ==================================================

    if state == FOLLOW_TRACK:


        # ------------------------------------------
        # CAMERA NAVIGATION
        # ------------------------------------------

        valid_track, error = (
            read_track()
        )


        if valid_track:

            action = track.follow(
                error,
                lap
            )

            print(
                "TRACK",
                "Error:",
                error,
                "Action:",
                action,
                "Lap:",
                lap
            )


        else:

            # One missed frame should not stop us.

            if lap == 1:

                speed = (
                    track.learning_speed
                )

            else:

                speed = (
                    track.fast_speed
                )

            car.forward(
                speed
            )

            print(
                "Track temporarily lost"
            )


        # ------------------------------------------
        # ULTRASONIC
        # ------------------------------------------

        distance = (
            update_front_distance()
        )


        # ------------------------------------------
        # EMERGENCY TURN
        # ------------------------------------------

        if distance <= EMERGENCY_CM:

            print("")
            print(
                "EMERGENCY WALL:",
                distance
            )

            print(
                "Forcing corner now"
            )


            record_corner()


            turn_saw_close_wall = False

            turn_started_ms = time.ticks_ms()


            drive_corner()


            state = TURNING

            continue


        # ------------------------------------------
        # WALL APPROACH
        # ------------------------------------------

        if distance <= WALL_DETECT_CM:

            print("")
            print(
                "Wall approaching:",
                distance
            )

            state = APPROACH_CORNER

            continue


    # ==================================================
    # APPROACH CORNER
    # ==================================================

    elif state == APPROACH_CORNER:


        # ------------------------------------------
        # CAMERA STILL CONTROLS ALIGNMENT
        # ------------------------------------------

        valid_track, error = (
            read_track()
        )


        if valid_track:

            if abs(error) <= 5:

                car.forward(
                    CORNER_APPROACH_SPEED
                )


            elif error < 0:

                car.diagonal_forward_left(
                    80
                )


            else:

                car.diagonal_forward_right(
                    80
                )


        else:

            car.forward(
                CORNER_APPROACH_SPEED
            )


        # ------------------------------------------
        # FRONT WALL
        # ------------------------------------------

        distance = (
            update_front_distance()
        )


        print(
            "CORNER APPROACH",
            "Distance:",
            distance
        )


        # ------------------------------------------
        # BEGIN TURN
        # ------------------------------------------

        if distance <= TURN_TRIGGER_CM:

            print("")
            print("==============================")
            print(
                "START CORNER",
                TURN_DIRECTION.upper()
            )

            print(
                "Wall:",
                distance,
                "cm"
            )

            print("==============================")
            print("")


            record_corner()


            # Reset the two-stage wall-release logic.

            turn_saw_close_wall = False

            turn_started_ms = time.ticks_ms()


            drive_corner()


            state = TURNING


    # ==================================================
    # TURNING
    # ==================================================

    elif state == TURNING:


        # ------------------------------------------
        # TIMEOUT
        # ------------------------------------------
        #
        # If the ultrasonic never sees the expected
        # close-then-release pattern, stop rotating
        # anyway instead of spinning forever.

        turn_elapsed = time.ticks_diff(
            time.ticks_ms(),
            turn_started_ms
        )

        if turn_elapsed >= TURN_TIMEOUT_MS:

            print("")
            print(
                "TURN: timeout, stopping rotation"
            )

            car.stop()

            time.sleep_ms(40)

            car.forward(
                RECOVERY_FORWARD_SPEED
            )

            recovery_started_ms = (
                time.ticks_ms()
            )

            state = TRACK_RECOVERY

            continue


        # ------------------------------------------
        # KEEP TAKING CORNER
        # ------------------------------------------

        drive_corner()


        # ------------------------------------------
        # READ ULTRASONIC DIRECTLY
        # ------------------------------------------
        #
        # We intentionally read it continuously
        # here because it determines when the turn
        # should finish.

        distance = (
            ultrasonic.get_stable_distance()
        )


        front_distance = distance


        print(
            "TURN",
            "Distance:",
            distance,
            "Close wall seen:",
            turn_saw_close_wall
        )


        # ------------------------------------------
        # STAGE 1
        #
        # Confirm that the sensor has actually
        # passed close to the old wall.
        # ------------------------------------------

        if not turn_saw_close_wall:

            if distance <= TURN_WALL_CLOSE_CM:

                turn_saw_close_wall = True

                print("")
                print(
                    "TURN: close wall confirmed",
                    distance,
                    "cm"
                )


        # ------------------------------------------
        # STAGE 2
        #
        # Once we have seen the close wall,
        # wait for the measured distance to rise.
        #
        # This means the ultrasonic is now looking
        # away from the old wall and toward the
        # new straight.
        # ------------------------------------------

        else:

            if distance >= TURN_WALL_RELEASE_CM:

                print("")
                print("==============================")
                print("TURN COMPLETE")
                print(
                    "Wall released at:",
                    distance,
                    "cm"
                )
                print("==============================")
                print("")


                # Stop steering.
                car.stop()

                time.sleep_ms(40)


                # Begin moving forward immediately.
                #
                # This gives the camera a stable
                # forward-facing view of the track.

                car.forward(
                    RECOVERY_FORWARD_SPEED
                )


                recovery_started_ms = (
                    time.ticks_ms()
                )


                state = TRACK_RECOVERY


    # ==================================================
    # TRACK RECOVERY
    # ==================================================

    elif state == TRACK_RECOVERY:


        now = time.ticks_ms()

        elapsed = time.ticks_diff(
            now,
            recovery_started_ms
        )


        # ------------------------------------------
        # MOVE FORWARD
        # ------------------------------------------

        car.forward(
            RECOVERY_FORWARD_SPEED
        )


        # ------------------------------------------
        # CAMERA
        # ------------------------------------------

        valid_track, error = (
            read_track()
        )


        # ------------------------------------------
        # CAMERA SEES TRACK
        # ------------------------------------------

        if valid_track:

            print(
                "RECOVERY",
                "Error:",
                error,
                "Elapsed:",
                elapsed
            )


            # --------------------------------------
            # CENTERED
            # --------------------------------------

            if abs(error) <= TRACK_CENTER_TOLERANCE:


                # Let the car travel forward briefly
                # after the turn before declaring
                # recovery complete.

                if elapsed >= RECOVERY_MIN_FORWARD_MS:

                    print("")
                    print("==============================")
                    print("TRACK REACQUIRED")
                    print(
                        "Error:",
                        error
                    )
                    print("==============================")
                    print("")


                    car.forward(
                        CORNER_EXIT_SPEED
                    )

                    time.sleep_ms(100)


                    finish_corner()


            # --------------------------------------
            # TRACK TO LEFT
            # --------------------------------------

            elif error < 0:

                car.diagonal_forward_left(
                    RECOVERY_CORRECTION_SPEED
                )


            # --------------------------------------
            # TRACK TO RIGHT
            # --------------------------------------

            else:

                car.diagonal_forward_right(
                    RECOVERY_CORRECTION_SPEED
                )


        # ------------------------------------------
        # CAMERA CANNOT SEE TRACK
        # ------------------------------------------

        else:

            print(
                "RECOVERY:",
                "moving forward, waiting for track"
            )


            # Keep going straight.
            #
            # Do NOT start another turn here.

            car.forward(
                RECOVERY_FORWARD_SPEED
            )


        # ------------------------------------------
        # SAFETY TIMEOUT
        # ------------------------------------------

        if elapsed >= RECOVERY_TIMEOUT_MS:

            print("")
            print(
                "Recovery timeout"
            )

            print(
                "Returning control to camera"
            )


            turn_saw_close_wall = False


            # We still count the physical corner
            # because the ultrasonic already
            # confirmed the turn was completed.

            corner_count += 1


            if corner_count >= CORNERS_PER_LAP:

                corner_count = 0

                complete_lap()


            straight_started_ms = (
                time.ticks_ms()
            )


            state = FOLLOW_TRACK


    # ==================================================
    # STANDARD LOOP DELAY
    # ==================================================

    time.sleep_ms(20)

